import struct, sys
sys.path.insert(0, 'tools')
from gen3save import Save, BoxMon, decode_text, SECTION
rom = open(sys.argv[2], 'rb').read()
print('refs to vanilla move-name table:', rom.count(struct.pack('<I', 0x081F8320)))
def move_name(m): return decode_text(rom[0x1F8320 + m * 13:0x1F8320 + m * 13 + 13])
def species_name(s): return decode_text(rom[0x1F716C + s * 11:0x1F716C + s * 11 + 11])
save = Save(open(sys.argv[1], 'rb').read())
for slot in (0, 1):
    print(f'slot {slot}: save index {save.slot_index(slot)}, bad checksums {save.verify_checksums(slot)}')
slot = save.latest_slot(); secs = save.slot_sections(slot)
print('latest slot', slot)
s1 = secs[1]
count = struct.unpack_from('<I', save.raw, s1 + 0x234)[0]
print('party size', count)
for i in range(count):
    m = BoxMon(save.raw, s1 + 0x238 + i * 100)
    mv, pp = m.moves()
    level = save.raw[s1 + 0x238 + i * 100 + 84]
    print(f'  party {i}: {species_name(m.species())} "{m.nickname}" Lv{level} ppBonus={m.pp_bonuses():08b} checksum_ok={m.checksum_ok()}')
    print('     moves:', [(x, move_name(x), p) for x, p in zip(mv, pp)])
# PC boxes: sections 5..13 data concatenated
pc = bytearray()
for sid in range(5, 14):
    pc += save.raw[secs[sid]:secs[sid] + 0xF80]
for b in range(14):
    for j in range(30):
        m = BoxMon(pc, 4 + (b * 30 + j) * 80)
        if m.personality == 0 and m.ot_id == 0: continue
        sp = m.species()
        if sp in (46, 47, 147, 148, 149):
            mv, pp = m.moves()
            print(f'  box {b+1} slot {j+1}: {species_name(sp)} "{m.nickname}"', [(x, move_name(x), p) for x, p in zip(mv, pp)])
