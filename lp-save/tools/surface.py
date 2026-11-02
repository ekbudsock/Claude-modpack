"""From each underwater surfacing spot, flood-fill Victory Road's water map and report what it leads to."""
import sys
from collections import deque
sys.path.insert(0, 'tools')
from mapgrid import Rom, Grid
rom = Rom(sys.argv[1]); start = (int(sys.argv[2]), int(sys.argv[3]))
under, surf = Grid(rom, 24, 46), Grid(rom, 24, 45)
uw = rom.warps(24, 46)
uwarp = {(x, y): (uw[d][0], uw[d][1]) for x, y, _, d, mn, mg in uw if (mg, mn) == (24, 46)}
# reachable underwater tiles
seen = {start}; q = deque([start])
while q:
    x, y = q.popleft()
    nbrs = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    if (x, y) in uwarp: nbrs.append(uwarp[(x, y)])
    for n in nbrs:
        if 0 <= n[0] < under.w and 0 <= n[1] < under.h and n not in seen and (under.collision(*n) == 0 or n in uwarp.values()):
            seen.add(n); q.append(n)
spots = [p for p in seen if under.behavior(*p) not in (0x19, 0x2A) and surf.collision(*p) == 0]
sw = rom.warps(24, 45)
# flood-fill the surface from each spot; group spots into surface regions
region_of = {}
regions = []
for s in sorted(spots):
    if s in region_of: continue
    reg = {s}; q = deque([s])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= n[0] < surf.w and 0 <= n[1] < surf.h and n not in reg and surf.collision(*n) == 0:
                reg.add(n); q.append(n)
    rid = len(regions); regions.append(reg)
    for p in spots:
        if p in reg: region_of[p] = rid
for rid, reg in enumerate(regions):
    entry = [p for p in spots if region_of[p] == rid]
    xs = [p[0] for p in reg]; ys = [p[1] for p in reg]
    warps_in = [(x, y, f'{mg}.{mn}') for x, y, _, _, mn, mg in sw if (x, y) in reg]
    edges = sorted({'east edge -> map 0.8' for p in reg if p[0] == surf.w - 1})
    land = sum(1 for p in reg if surf.behavior(*p) not in (0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16))
    print(f'surface region {rid}: {len(reg)} tiles x{min(xs)}-{max(xs)} y{min(ys)}-{max(ys)}, land tiles {land}, '
          f'surfacing spots {len(entry)} e.g. {sorted(entry, key=lambda p: abs(p[0]-start[0])+abs(p[1]-start[1]))[:3]}, '
          f'warps {warps_in}, {edges}')
