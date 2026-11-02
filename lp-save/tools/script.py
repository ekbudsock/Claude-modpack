"""Minimal Gen 3 (Ruby) event-script disassembler, enough to read map and trainer scripts.

usage: script.py <rom> mapscripts <group> <num>   |   script.py <rom> at <hexaddr> [count]
"""
import struct
import sys

sys.path.insert(0, 'tools')
from mapgrid import Rom  # noqa: E402

# opcode: (name, argument layout)  b=u8 h=u16 w=u32/pointer
OPS = {
    0x00: ('nop', ''), 0x01: ('nop1', ''), 0x02: ('end', ''), 0x03: ('return', ''),
    0x04: ('call', 'w'), 0x05: ('goto', 'w'), 0x06: ('goto_if', 'bw'), 0x07: ('call_if', 'bw'),
    0x08: ('gotostd', 'b'), 0x09: ('callstd', 'b'), 0x0A: ('gotostd_if', 'bb'), 0x0B: ('callstd_if', 'bb'),
    0x0C: ('returnram', ''), 0x0D: ('killscript', ''), 0x0E: ('setmysteryeventstatus', 'b'),
    0x0F: ('loadword', 'bw'), 0x10: ('loadbyte', 'bb'), 0x11: ('writebytetoaddr', 'bw'),
    0x12: ('loadbytefromaddr', 'bw'), 0x13: ('setptrbyte', 'bw'), 0x14: ('copylocal', 'bb'),
    0x15: ('copybyte', 'ww'), 0x16: ('setvar', 'hh'), 0x17: ('addvar', 'hh'), 0x18: ('subvar', 'hh'),
    0x19: ('copyvar', 'hh'), 0x1A: ('setorcopyvar', 'hh'), 0x1B: ('compare_local_to_local', 'bb'),
    0x1C: ('compare_local_to_value', 'bb'), 0x1D: ('compare_local_to_addr', 'bw'),
    0x1E: ('compare_addr_to_local', 'wb'), 0x1F: ('compare_addr_to_value', 'wb'),
    0x20: ('compare_addr_to_addr', 'ww'), 0x21: ('compare_var_to_value', 'hh'),
    0x22: ('compare_var_to_var', 'hh'), 0x23: ('callnative', 'w'), 0x24: ('gotonative', 'w'),
    0x25: ('special', 'h'), 0x26: ('specialvar', 'hh'), 0x27: ('waitstate', ''), 0x28: ('delay', 'h'),
    0x29: ('setflag', 'h'), 0x2A: ('clearflag', 'h'), 0x2B: ('checkflag', 'h'),
    0x2C: ('initclock', 'hh'), 0x2D: ('dotimebasedevents', ''), 0x2E: ('gettime', ''),
    0x2F: ('playse', 'h'), 0x30: ('waitse', ''), 0x31: ('playfanfare', 'h'), 0x32: ('waitfanfare', ''),
    0x33: ('playbgm', 'hb'), 0x34: ('savebgm', 'h'), 0x35: ('fadedefaultbgm', ''), 0x36: ('fadenewbgm', 'h'),
    0x37: ('fadeoutbgm', 'b'), 0x38: ('fadeinbgm', 'b'), 0x39: ('warp', 'bbbhh'), 0x3A: ('warpsilent', 'bbbhh'),
    0x3B: ('warpdoor', 'bbbhh'), 0x3C: ('warphole', 'bb'), 0x3D: ('warpteleport', 'bbbhh'),
    0x3E: ('setwarp', 'bbbhh'), 0x3F: ('setdynamicwarp', 'bbbhh'), 0x40: ('setdivewarp', 'bbbhh'),
    0x41: ('setholewarp', 'bbbhh'), 0x42: ('getplayerxy', 'hh'), 0x43: ('getpartysize', ''),
    0x44: ('additem', 'hh'), 0x45: ('removeitem', 'hh'), 0x46: ('checkitemspace', 'hh'),
    0x47: ('checkitem', 'hh'), 0x48: ('checkitemtype', 'h'), 0x49: ('addpcitem', 'hh'),
    0x4A: ('checkpcitem', 'hh'), 0x4B: ('adddecoration', 'h'), 0x4C: ('removedecoration', 'h'),
    0x4D: ('testdecoration', 'h'), 0x4E: ('checkdecor', 'h'), 0x4F: ('applymovement', 'hw'),
    0x50: ('applymovementpos', 'hwbb'), 0x51: ('waitmovement', 'h'), 0x52: ('waitmovementpos', 'hbb'),
    0x53: ('removeobject', 'h'), 0x54: ('removeobjectpos', 'hbb'), 0x55: ('addobject', 'h'),
    0x56: ('addobjectpos', 'hbb'), 0x57: ('setobjectxy', 'hhh'), 0x58: ('showobjectat', 'hbb'),
    0x59: ('hideobjectat', 'hbb'), 0x5A: ('faceplayer', ''), 0x5B: ('turnobject', 'hb'),
    0x5D: ('dotrainerbattle', ''), 0x5E: ('gotopostbattlescript', ''), 0x5F: ('gotobeatenscript', ''),
    0x60: ('checktrainerflag', 'h'), 0x61: ('settrainerflag', 'h'), 0x62: ('cleartrainerflag', 'h'),
    0x63: ('setobjectxyperm', 'hhh'), 0x64: ('moveobjectoffscreen', 'h'), 0x65: ('setobjectmovementtype', 'hb'),
    0x66: ('waitmessage', ''), 0x67: ('message', 'w'), 0x68: ('closemessage', ''), 0x69: ('lockall', ''),
    0x6A: ('lock', ''), 0x6B: ('releaseall', ''), 0x6C: ('release', ''), 0x6D: ('waitbuttonpress', ''),
    0x6E: ('yesnobox', 'bb'), 0x6F: ('multichoice', 'bbbb'), 0x75: ('showmonpic', 'hbb'),
    0x76: ('hidemonpic', ''), 0x79: ('givemon', 'hbhwwb'), 0x7C: ('checkpartymove', 'h'),
    0x7D: ('bufferspeciesname', 'bh'), 0x80: ('bufferitemname', 'bh'), 0x82: ('buffermovename', 'bh'),
    0x8F: ('random', 'h'), 0x90: ('givemoney', 'wb'), 0x96: ('getpricereduction', 'h'),
    0x97: ('fadescreen', 'b'), 0x99: ('setflashlevel', 'h'), 0xA1: ('playmoncry', 'hh'),
    0x9F: ('setrespawn', 'h'), 0xA2: ('setmetatile', 'hhhh'), 0xA3: ('resetweather', ''), 0xA4: ('setweather', 'h'),
    0xA5: ('doweather', ''), 0xA6: ('setstepcallback', 'b'), 0xA7: ('setmaplayoutindex', 'h'),
    0xA8: ('setobjectpriority', 'hbbb'), 0xA9: ('resetobjectpriority', 'hbb'), 0xAA: ('createvobject', 'bbhhbb'),
    0xAB: ('turnvobject', 'bb'), 0xAC: ('opendoor', 'hh'), 0xAD: ('closedoor', 'hh'), 0xAE: ('waitdooranim', ''),
    0xAF: ('setdooropen', 'hh'), 0xB0: ('setdoorclosed', 'hh'), 0xB6: ('setwildbattle', 'hbh'),
    0xB7: ('dowildbattle', ''), 0xC5: ('waitmoncry', ''),
}
SIZES = {'b': 1, 'h': 2, 'w': 4}
TRAINERBATTLE_PTRS = {0: 2, 1: 3, 2: 3, 3: 1, 4: 3, 5: 2, 6: 4, 7: 3, 8: 4}


def disasm(rom, addr, count=60):
    o = addr - 0x08000000
    out = []
    for _ in range(count):
        op = rom.d[o]
        start = o
        o += 1
        if op == 0x5C:  # trainerbattle type, trainer, local id, then 1-4 pointers
            kind, trainer, local = rom.d[o], *struct.unpack_from('<HH', rom.d, o + 1)
            o += 5
            ptrs = [rom.u32(o + 4 * i) for i in range(TRAINERBATTLE_PTRS.get(kind, 2))]
            o += 4 * len(ptrs)
            out.append((start, f'trainerbattle type={kind} trainer={trainer} {" ".join(hex(p) for p in ptrs)}'))
            continue
        if op not in OPS:
            out.append((start, f'.byte {op:#04x}  (unknown opcode, stopping)'))
            break
        name, args = OPS[op]
        vals = []
        for a in args:
            v = rom.d[o] if a == 'b' else struct.unpack_from('<H', rom.d, o)[0] if a == 'h' else rom.u32(o)
            vals.append(hex(v))
            o += SIZES[a]
        out.append((start, f'{name} {", ".join(vals)}'))
        if op in (0x02, 0x03, 0x05, 0x08):
            break
    return out


def map_scripts(rom, group, num):
    ms = rom.u32(rom.header(group, num) + 8) - 0x08000000
    res = []
    while rom.d[ms]:
        kind, ptr = rom.d[ms], rom.u32(ms + 1)
        ms += 5
        if kind in (2, 4):
            entries = []
            t = ptr - 0x08000000
            while struct.unpack_from('<H', rom.d, t)[0]:
                var, val = struct.unpack_from('<HH', rom.d, t)
                entries.append((var, val, rom.u32(t + 4)))
                t += 8
            res.append((kind, ptr, entries))
        else:
            res.append((kind, ptr, None))
    return res


if __name__ == '__main__':
    rom = Rom(sys.argv[1])
    if sys.argv[2] == 'at':
        for a, text in disasm(rom, int(sys.argv[3], 16), int(sys.argv[4]) if len(sys.argv) > 4 else 60):
            print(f'  {0x08000000 + a:08X}: {text}')
    else:
        names = {1: 'ON_LOAD', 2: 'ON_FRAME_TABLE', 3: 'ON_TRANSITION', 4: 'ON_WARP_INTO_MAP_TABLE', 5: 'ON_RESUME'}
        for kind, ptr, entries in map_scripts(rom, int(sys.argv[3]), int(sys.argv[4])):
            print(f'{names.get(kind, kind)} @ {ptr:#010x}')
            if entries:
                for var, val, sp in entries:
                    print(f'   if var {var:#06x} == {val}: {sp:#010x}')
