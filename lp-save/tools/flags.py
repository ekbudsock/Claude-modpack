"""Read/write SaveBlock1 flags (stored from SaveBlock1+0x1220, one bit each) across sections 1-4."""
import sys
sys.path.insert(0, 'tools')
from gen3save import Save

def sb1_offset(save, slot, off):
    secs = save.slot_sections(slot)
    return secs[1 + off // 0xF80] + off % 0xF80, 1 + off // 0xF80

def get_flag(save, slot, flag):
    pos, _ = sb1_offset(save, slot, 0x1220 + flag // 8)
    return (save.raw[pos] >> (flag % 8)) & 1

def set_flag(save, slot, flag, value):
    pos, sid = sb1_offset(save, slot, 0x1220 + flag // 8)
    if value:
        save.raw[pos] |= 1 << (flag % 8)
    else:
        save.raw[pos] &= ~(1 << (flag % 8)) & 0xFF
    save.fix_checksum(save.slot_sections(slot)[sid], sid)

if __name__ == '__main__':
    save = Save(open(sys.argv[1], 'rb').read())
    slot = save.latest_slot()
    for f in sys.argv[2:]:
        print(f'flag {f}: {get_flag(save, slot, int(f, 16))}')
