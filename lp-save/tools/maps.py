"""List every map (group.num) with its region-map section name.

gMapGroups -> per-group arrays of MapHeader pointers; MapHeader.regionMapSectionId is at +0x14;
gRegionMapEntries entries are 8 bytes with the name pointer at +4.
"""
import struct, sys
sys.path.insert(0, 'tools')
from gen3save import decode_text
rom = open(sys.argv[1], 'rb').read()
MAP_GROUPS, REGION_ENTRIES = 0x308588, 0x3E73C4
def u32(off): return struct.unpack_from('<I', rom, off)[0]
def is_rom_ptr(p): return 0x08000000 <= p < 0x09000000
group_ptrs = []
i = 0
while is_rom_ptr(u32(MAP_GROUPS + i * 4)):
    group_ptrs.append(u32(MAP_GROUPS + i * 4) - 0x08000000); i += 1
starts = sorted(set(group_ptrs)) + [MAP_GROUPS]
def section_name(sec):
    if sec >= 0x58: return f'(section {sec})'
    p = u32(REGION_ENTRIES + sec * 8 + 4)
    return decode_text(rom[p - 0x08000000:p - 0x08000000 + 24]) if is_rom_ptr(p) else f'(section {sec})'
want = sys.argv[2:] if len(sys.argv) > 2 else None
for g, gp in enumerate(group_ptrs):
    nxt = min([s for s in starts if s > gp] or [gp + 4 * 64])
    for n in range((nxt - gp) // 4):
        h = u32(gp + n * 4)
        if not is_rom_ptr(h): break
        h -= 0x08000000
        sec = rom[h + 0x14]
        name = section_name(sec)
        tag = f'{g}.{n}'
        if want is None or tag in want or any(w.upper() in name.upper() for w in want):
            layout = u32(h); w_, hgt = (struct.unpack_from('<II', rom, layout - 0x08000000) if is_rom_ptr(layout) else (0, 0))
            print(f'{tag:7} {name:22} section={sec} size={w_}x{hgt}')
