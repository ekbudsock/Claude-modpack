"""Build the Light Platinum Elite Four 'exit to the lobby' cheat (map 16.9 holds the whole Elite Four).

- Metatile 0x341 (the bottom entrance tile of every room and hall) becomes a south arrow warp.
- The bottom warps of the four member rooms and the halls lead to the League lobby (16.10, warp 2).
- Each member's 'already beaten -> just talk' check becomes 'always battle' (goto_if condition 3 is
  true for both flag states), so returning to a room whose exit has reset can't soft-lock.

Prints the cheat as mGBA 'ADDRESS:VALUE' lines (built from the ROM's own bytes, so untouched
neighbouring bytes are written back unchanged).
usage: e4_lobby_patch.py <rom.gba>
"""
import struct
import sys

rom = open(sys.argv[1], 'rb').read()
patch = {}  # ROM address -> new byte


def put(addr, data):
    for i, b in enumerate(data):
        patch[addr + i] = b


ARROW_ATTR = 0x082863AA                      # attributes of metatile 0x341
assert struct.unpack_from('<H', rom, ARROW_ATTR - 0x08000000)[0] == 0x1000
put(ARROW_ATTR, struct.pack('<H', 0x1065))   # MB_SOUTH_ARROW_WARP

WARPS = 0x08B143E8                           # map 16.9 warp table, 8 bytes per warp
for i in (2, 5, 8, 11, 3, 6, 9, 13):        # room bottoms, then hall bottoms
    entry = WARPS + i * 8
    x, y = struct.unpack_from('<hh', rom, entry - 0x08000000)
    assert y == 12, (i, x, y)
    put(entry + 5, bytes([2, 10, 16]))       # -> warp 2 of map 16.10 (League lobby)

for goto_if in (0x08A8B191, 0x08A8B48F, 0x08A8B761, 0x08A8BA3A):
    o = goto_if - 0x08000000
    assert rom[o] == 0x06 and rom[o + 1] == 0x00, hex(goto_if)
    put(goto_if + 1, bytes([3]))             # condition 'lt' -> 'le' (always true after checkflag)

lines = []
addrs = sorted(patch)
done = set()
for a in addrs:
    if a in done:
        continue
    word = a & ~3
    if sum((word + k) in patch for k in range(4)) > 2:  # most of the word changes: write all 4 bytes
        start, size = word, 4
    else:
        start, size = a & ~1, 2
    data = bytes(patch.get(start + k, rom[start - 0x08000000 + k]) for k in range(size))
    value = int.from_bytes(data, 'little')
    lines.append(f'{start:08X}:{value:0{size * 2}X}')
    done.update(range(start, start + size))
print('\n'.join(lines))
