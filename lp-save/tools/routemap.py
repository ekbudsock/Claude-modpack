"""Draw a schematic of the underwater + surface route (walls dark, open tiles light, seaweed green, route red)."""
import sys, ast
from PIL import Image, ImageDraw
sys.path.insert(0, 'tools')
from mapgrid import Rom, Grid
rom = Rom(sys.argv[1]); out = sys.argv[2]
under, surf = Grid(rom, 24, 46), Grid(rom, 24, 45)
S = 7
def panel(g, title, water_mbs):
    img = Image.new('RGB', (g.w * S, g.h * S + 22), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((4, 4), title, fill=(0, 0, 0))
    for y in range(g.h):
        for x in range(g.w):
            mb, col = g.behavior(x, y), g.collision(x, y)
            if col: c = (60, 60, 70)
            elif mb in (0x22, 0x2A): c = (90, 170, 90)
            elif mb in water_mbs: c = (120, 170, 230)
            else: c = (225, 210, 160) if g is surf else (150, 190, 230)
            d.rectangle([x * S, 22 + y * S, x * S + S - 1, 22 + y * S + S - 1], fill=c)
    return img, d
def dot(d, p, c, r=4):
    d.ellipse([p[0] * S + S // 2 - r, 22 + p[1] * S + S // 2 - r, p[0] * S + S // 2 + r, 22 + p[1] * S + S // 2 + r], fill=c, outline=(0, 0, 0))
def line(d, path):
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1:
            d.line([a[0] * S + S // 2, 22 + a[1] * S + S // 2, b[0] * S + S // 2, 22 + b[1] * S + S // 2], fill=(220, 30, 30), width=3)
under_path = ast.literal_eval(sys.argv[3]); surf_path = ast.literal_eval(sys.argv[4])
u_img, ud = panel(under, '1) UNDERWATER - follow the red line. Yellow = step on the dark arch (warp). Pink = arrive. Star = press B to surface', ())
line(ud, under_path)
for a, b in zip(under_path, under_path[1:]):
    if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1: dot(ud, a, (250, 220, 0), 5); dot(ud, b, (250, 120, 200), 5)
dot(ud, under_path[0], (255, 255, 255), 6); dot(ud, under_path[-1], (255, 60, 60), 7)
s_img, sd = panel(surf, '2) SURFACE (Surf) - follow the red line east to the beach, then walk right to the League. Swimmer + Red battles on the way', (0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16))
line(sd, surf_path)
dot(sd, surf_path[0], (255, 60, 60), 7); dot(sd, surf_path[-1], (250, 220, 0), 6)
img = Image.new('RGB', (u_img.width, u_img.height + s_img.height + 10), (255, 255, 255))
img.paste(u_img, (0, 0)); img.paste(s_img, (0, u_img.height + 10))
img.save(out)
