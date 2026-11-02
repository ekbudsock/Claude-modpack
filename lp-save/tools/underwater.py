"""Flood-fill the underwater map from the player's position (following warp tiles) and list surfacing spots."""
import sys
from collections import deque
sys.path.insert(0, 'tools')
from mapgrid import Rom, Grid
rom = Rom(sys.argv[1]); start = (int(sys.argv[2]), int(sys.argv[3]))
G, N, SG, SN = 24, 46, 24, 45
under, surf = Grid(rom, G, N), Grid(rom, SG, SN)
warps = rom.warps(G, N)
warp_at = {(x, y): (warps[dst][0], warps[dst][1]) for x, y, _, dst, mn, mg in warps if (mg, mn) == (G, N)}
NO_SURFACING = (0x19, 0x2A)
seen = {start}; q = deque([start]); used_warps = []
while q:
    x, y = q.popleft()
    if (x, y) in warp_at:
        t = warp_at[(x, y)]
        used_warps.append(((x, y), t))
        if t not in seen: seen.add(t); q.append(t)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < under.w and 0 <= ny < under.h and (nx, ny) not in seen and under.collision(nx, ny) == 0:
            seen.add((nx, ny)); q.append((nx, ny))
print(f'map {under.w}x{under.h}; reachable tiles: {len(seen)}')
print('warps used:', used_warps)
spots = [(x, y) for x, y in sorted(seen) if under.behavior(x, y) not in NO_SURFACING]
print(f'tiles where B (surface) is allowed: {len(spots)}')
for x, y in spots[:60]:
    print(f'   ({x},{y}) underwater mb={under.behavior(x, y):#04x} -> surface tile mb={surf.behavior(x, y):#04x} collision={surf.collision(x, y)}')
from collections import Counter
print('behaviors of reachable tiles:', Counter(f'{under.behavior(x, y):#04x}' for x, y in seen).most_common())
