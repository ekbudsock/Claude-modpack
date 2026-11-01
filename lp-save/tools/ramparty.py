import struct, sys
sys.path.insert(0, 'tools')
from gen3save import BoxMon, decode_text
rom = open(sys.argv[1], 'rb').read()
ram = bytearray(open(sys.argv[2], 'rb').read())
count = ram[0]
print('party count in RAM:', count)
for i in range(count):
    m = BoxMon(ram, 0x10 + i * 100)
    mv, pp = m.moves()
    sp = decode_text(rom[0x1F716C + m.species() * 11:][:11])
    print(f'  {sp} "{m.nickname}" Lv{ram[0x10 + i*100 + 84]} checksum_ok={m.checksum_ok()}', [(decode_text(rom[0x1F8320 + x*13:][:13]), p) for x, p in zip(mv, pp)])
