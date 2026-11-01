"""List every Pokemon in the latest save slot with its raw nickname bytes and language."""
import struct, sys
sys.path.insert(0, 'tools')
from gen3save import Save, BoxMon, decode_text
rom = open(sys.argv[2], 'rb').read()
save = Save(open(sys.argv[1], 'rb').read())
secs = save.slot_sections(save.latest_slot())
def species_name(s): return decode_text(rom[0x1F716C + s * 11:0x1F716C + s * 11 + 11])
def show(label, m):
    nick = bytes(m.buf[m.off + 8:m.off + 18])
    lang = m.buf[m.off + 18]
    flags = m.buf[m.off + 19]
    print(f'{label:14} {species_name(m.species()):11} nick="{m.nickname}" raw={nick.hex(" ")} lang={lang} flags={flags:02x}')
s1 = secs[1]
for i in range(struct.unpack_from('<I', save.raw, s1 + 0x234)[0]):
    show(f'party {i+1}', BoxMon(save.raw, s1 + 0x238 + i * 100))
pc = bytearray()
for sid in range(5, 14):
    pc += save.raw[secs[sid]:secs[sid] + 0xF80]
for b in range(14):
    for j in range(30):
        m = BoxMon(pc, 4 + (b * 30 + j) * 80)
        if m.personality or m.ot_id:
            show(f'box {b+1}-{j+1}', m)
