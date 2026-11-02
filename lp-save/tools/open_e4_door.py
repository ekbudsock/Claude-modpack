"""Re-open the entrance door of an Elite Four room inside a save's stored map view.

On Continue the game restores the tiles saved around the player (SaveBlock1.mapView, 15x14 blocks
starting at backup-map coords pos.x, pos.y) before the room's load script runs, so a door that was
closed when the game was saved stays closed. This writes the room's original layout blocks back
over the door tiles (5..7, 12..13).

usage: open_e4_door.py <rom.gba> <in.srm> <out.srm>
"""
import struct
import sys

sys.path.insert(0, 'tools')
from gen3save import Save  # noqa: E402
from mapgrid import Rom, Grid  # noqa: E402

VIEW_W, VIEW_H, OFFSET = 15, 14, 7
DOOR_TILES = [(x, y) for y in (12, 13) for x in (5, 6, 7)]

rom = Rom(sys.argv[1])
save = Save(open(sys.argv[2], 'rb').read())
slot = save.latest_slot()
s1 = save.slot_sections(slot)[1]
px, py = struct.unpack_from('<hh', save.raw, s1)
group, num = struct.unpack_from('<bb', save.raw, s1 + 4)
assert group == 16 and 0 <= num <= 3, f'not in an Elite Four room (map {group}.{num})'
room = Grid(rom, group, num)
changed = 0
for mx, my in DOOR_TILES:
    vx, vy = mx + OFFSET - px, my + OFFSET - py
    if 0 <= vx < VIEW_W and 0 <= vy < VIEW_H:
        off = s1 + 0x34 + 2 * (vy * VIEW_W + vx)
        old = struct.unpack_from('<H', save.raw, off)[0]
        new = room.blocks[my * room.w + mx]
        struct.pack_into('<H', save.raw, off, new)
        print(f'door tile ({mx},{my}): {old:#06x} -> {new:#06x}')
        changed += 1
save.fix_checksum(s1, 1)
assert save.verify_checksums(slot) == []
open(sys.argv[3], 'wb').write(save.raw)
print(f'map {group}.{num} pos ({px},{py}); {changed} door tiles restored')
