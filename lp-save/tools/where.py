"""Show location, money and play time for both save slots."""
import struct, sys
sys.path.insert(0, 'tools')
from gen3save import Save
save = Save(open(sys.argv[1], 'rb').read())
for slot in (0, 1):
    secs = save.slot_sections(slot)
    if len(secs) != 14:
        print(f'slot {slot}: incomplete'); continue
    s0, s1 = secs[0], secs[1]
    h, m, s = struct.unpack_from('<HBB', save.raw, s0 + 0x0E)
    x, y = struct.unpack_from('<hh', save.raw, s1 + 0x00)
    grp, num, warp = struct.unpack_from('<bbb', save.raw, s1 + 0x04)
    heal = struct.unpack_from('<bbb', save.raw, s1 + 0x1C)
    money = struct.unpack_from('<I', save.raw, s1 + 0x490)[0]
    print(f'slot {slot}: index {save.slot_index(slot)} bad={save.verify_checksums(slot)} playtime {h}:{m:02d}:{s:02d} '
          f'map {grp}.{num} warp {warp} pos ({x},{y}) lastHeal {heal[0]}.{heal[1]} money {money}')
