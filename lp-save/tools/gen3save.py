"""Read and edit Pokemon Ruby-based (Light Platinum) save files.

Save layout: two slots of 14 sections x 0x1000 bytes. Each section ends with
id (u16) @0xFF4, checksum (u16) @0xFF6, signature 0x08012025 @0xFF8, save index (u32) @0xFFC.
"""
import struct

SECTION = 0x1000
SIGNATURE = 0x08012025
# bytes of each section that are checksummed (Ruby/Sapphire)
SECTION_SIZES = [0x890, 0xF80, 0xF80, 0xF80, 0xC40] + [0xF80] * 8 + [0x7D0]
SUBSTRUCT_ORDERS = ['GAEM', 'GAME', 'GEAM', 'GEMA', 'GMAE', 'GMEA', 'AGEM', 'AGME', 'AEGM', 'AEMG',
                    'AMGE', 'AMEG', 'EGAM', 'EGMA', 'EAGM', 'EAMG', 'EMGA', 'EMAG', 'MGAE', 'MGEA',
                    'MAGE', 'MAEG', 'MEGA', 'MEAG']
CHARMAP = {0: ' ', 0xAD: '.', 0xAE: '-', 0xB4: "'", 0xB5: '(M)', 0xB6: '(F)'}


def decode_text(b):
    out = ''
    for c in b:
        if c == 0xFF:
            break
        if 0xBB <= c <= 0xD4:
            out += chr(ord('A') + c - 0xBB)
        elif 0xD5 <= c <= 0xEE:
            out += chr(ord('a') + c - 0xD5)
        elif 0xA1 <= c <= 0xAA:
            out += chr(ord('0') + c - 0xA1)
        else:
            out += CHARMAP.get(c, '?')
    return out


def section_checksum(data, size):
    total = sum(struct.unpack_from('<%dI' % (size // 4), data, 0)) & 0xFFFFFFFF
    return ((total >> 16) + (total & 0xFFFF)) & 0xFFFF


class Save:
    def __init__(self, raw):
        self.raw = bytearray(raw)

    def slot_sections(self, slot):
        """Map section id -> byte offset for one save slot."""
        out = {}
        for i in range(14):
            off = slot * 14 * SECTION + i * SECTION
            sid, _, sig, _ = struct.unpack_from('<HHII', self.raw, off + 0xFF4)
            if sig == SIGNATURE:
                out[sid] = off
        return out

    def slot_index(self, slot):
        secs = self.slot_sections(slot)
        if len(secs) != 14:
            return -1
        return struct.unpack_from('<I', self.raw, next(iter(secs.values())) + 0xFFC)[0]

    def latest_slot(self):
        return max((0, 1), key=self.slot_index)

    def verify_checksums(self, slot):
        bad = []
        for sid, off in self.slot_sections(slot).items():
            stored = struct.unpack_from('<H', self.raw, off + 0xFF6)[0]
            if section_checksum(self.raw[off:off + SECTION], SECTION_SIZES[sid]) != stored:
                bad.append(sid)
        return bad

    def fix_checksum(self, off, sid):
        struct.pack_into('<H', self.raw, off + 0xFF6,
                         section_checksum(self.raw[off:off + SECTION], SECTION_SIZES[sid]))


class BoxMon:
    """An 80-byte box Pokemon (the first 80 bytes of a party Pokemon) inside a bytearray."""

    def __init__(self, buf, off):
        self.buf, self.off = buf, off

    @property
    def personality(self):
        return struct.unpack_from('<I', self.buf, self.off)[0]

    @property
    def ot_id(self):
        return struct.unpack_from('<I', self.buf, self.off + 4)[0]

    @property
    def nickname(self):
        return decode_text(self.buf[self.off + 8:self.off + 18])

    def decrypted(self):
        key = self.personality ^ self.ot_id
        words = struct.unpack_from('<12I', self.buf, self.off + 32)
        return bytearray(struct.pack('<12I', *(w ^ key for w in words)))

    def substruct(self, data, kind):
        i = SUBSTRUCT_ORDERS[self.personality % 24].index(kind)
        return i * 12

    def checksum_ok(self):
        data = self.decrypted()
        return sum(struct.unpack('<24H', data)) & 0xFFFF == struct.unpack_from('<H', self.buf, self.off + 28)[0]

    def species(self):
        data = self.decrypted()
        return struct.unpack_from('<H', data, self.substruct(data, 'G'))[0]

    def pp_bonuses(self):
        data = self.decrypted()
        return data[self.substruct(data, 'G') + 8]

    def moves(self):
        data = self.decrypted()
        a = self.substruct(data, 'A')
        return list(struct.unpack_from('<4H', data, a)), list(data[a + 8:a + 12])

    def set_move(self, slot, move, pp):
        data = self.decrypted()
        a = self.substruct(data, 'A')
        struct.pack_into('<H', data, a + slot * 2, move)
        data[a + 8 + slot] = pp
        struct.pack_into('<H', self.buf, self.off + 28, sum(struct.unpack('<24H', data)) & 0xFFFF)
        key = self.personality ^ self.ot_id
        words = struct.unpack('<12I', data)
        struct.pack_into('<12I', self.buf, self.off + 32, *(w ^ key for w in words))
