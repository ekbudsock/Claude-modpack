"""Shortest underwater route (with warp tiles) from the player to a surfacing spot that leads to the League."""
import sys
from collections import deque
sys.path.insert(0, 'tools')
from mapgrid import Rom, Grid
rom = Rom(sys.argv[1]); start = (int(sys.argv[2]), int(sys.argv[3]))
under, surf = Grid(rom, 24, 46), Grid(rom, 24, 45)
uw = rom.warps(24, 46)
uwarp = {(x, y): (uw[d][0], uw[d][1]) for x, y, _, d, mn, mg in uw if (mg, mn) == (24, 46)}
# arriving through a warp puts the player one tile below the destination warp tile
uwarp = {k: (v[0], v[1] + 1) for k, v in uwarp.items()}
# surface tiles connected to the east edge (exit to the League)
league = Grid(rom, 0, 8)  # east connection; only rows passable on both sides can be crossed
good = set(); q = deque([(99, y) for y in range(min(surf.h, league.h)) if surf.collision(99, y) == 0 and league.collision(0, y) == 0]); good.update(q)
while q:
    x, y = q.popleft()
    for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= n[0] < surf.w and 0 <= n[1] < surf.h and n not in good and surf.collision(*n) == 0:
            good.add(n); q.append(n)
prev = {start: None}; q = deque([start]); goal = None
while q:
    p = q.popleft()
    if under.behavior(*p) not in (0x19, 0x2A) and p in good and p not in uwarp:
        goal = p; break
    x, y = p
    nbrs = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    if p in uwarp: nbrs.append(uwarp[p])
    for n in nbrs:
        if 0 <= n[0] < under.w and 0 <= n[1] < under.h and n not in prev and (under.collision(*n) == 0 or n in uwarp.values()):
            prev[n] = p; q.append(n)
path = []
while goal: path.append(goal); goal = prev[goal]
path.reverse()
print('route:', path)
print('steps:', len(path) - 1)
