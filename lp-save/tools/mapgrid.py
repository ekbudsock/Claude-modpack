"""Map grid helpers for Ruby-based ROMs: per-tile metatile behavior and collision."""
import struct

MAP_GROUPS = 0x308588
NUM_PRIMARY_METATILES = 0x200


class Rom:
    def __init__(self, path):
        self.d = open(path, 'rb').read()

    def u32(self, off):
        return struct.unpack_from('<I', self.d, off)[0]

    def header(self, group, num):
        return self.u32(self.u32(MAP_GROUPS + group * 4) - 0x08000000 + num * 4) - 0x08000000

    def warps(self, group, num):
        ev = self.u32(self.header(group, num) + 4) - 0x08000000
        base = self.u32(ev + 8) - 0x08000000
        return [struct.unpack_from('<hhBBBB', self.d, base + i * 8) for i in range(self.d[ev + 1])]


class Grid:
    def __init__(self, rom, group, num):
        h = rom.header(group, num)
        layout = rom.u32(h) - 0x08000000
        self.w, self.h = struct.unpack_from('<II', rom.d, layout)
        blocks = rom.u32(layout + 12) - 0x08000000
        self.blocks = struct.unpack_from('<%dH' % (self.w * self.h), rom.d, blocks)
        self.attrs = []
        for ts in (rom.u32(layout + 16), rom.u32(layout + 20)):
            a = rom.u32(ts - 0x08000000 + 0x10) - 0x08000000
            self.attrs.append(a)
        self.rom = rom

    def metatile(self, x, y):
        return self.blocks[y * self.w + x] & 0x3FF

    def collision(self, x, y):
        return (self.blocks[y * self.w + x] >> 10) & 3

    def behavior(self, x, y):
        m = self.metatile(x, y)
        base, idx = (self.attrs[0], m) if m < NUM_PRIMARY_METATILES else (self.attrs[1], m - NUM_PRIMARY_METATILES)
        return self.rom.d[base + idx * 2]
