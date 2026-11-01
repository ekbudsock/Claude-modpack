"""Make Continue warp the player to a given map, using the game's own continue-game warp.

Sets SaveBlock2.specialSaveWarp (+0x09) = 1 and SaveBlock1.warp1 (+0x0C) to the destination.
usage: warp.py <in.srm> <out.srm> <mapGroup> <mapNum> <warpId> <x> <y>  (warpId -1 = use x,y)
"""
import struct, sys
sys.path.insert(0, 'tools')
from gen3save import Save
src, dst, group, num, warp_id, x, y = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
save = Save(open(src, 'rb').read())
slot = save.latest_slot(); secs = save.slot_sections(slot)
save.raw[secs[0] + 0x09] = 1
struct.pack_into('<bbbbhh', save.raw, secs[1] + 0x0C, group, num, warp_id, 0, x, y)
save.fix_checksum(secs[0], 0)
save.fix_checksum(secs[1], 1)
assert save.verify_checksums(slot) == []
open(dst, 'wb').write(save.raw)
