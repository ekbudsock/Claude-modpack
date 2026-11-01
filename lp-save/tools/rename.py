"""Reset broken nicknames in the party to the species name."""
import struct, sys
sys.path.insert(0, 'tools')
from gen3save import Save, BoxMon

def encode(text):
    out = bytes(0xBB + ord(c) - ord('A') for c in text)
    return out + b'\xff' * (10 - len(out))

src, dst = sys.argv[1], sys.argv[2]
save = Save(open(src, 'rb').read())
slot = save.latest_slot(); s1 = save.slot_sections(slot)[1]
for idx, species, name in [(3, 246 + 1, 'PUPITAR'), (4, 47, 'ZOROARK')]:
    m = BoxMon(save.raw, s1 + 0x238 + idx * 100)
    assert m.species() == species and m.nickname.startswith('s'), (idx, m.species(), m.nickname)
    save.raw[m.off + 8:m.off + 18] = encode(name)
    assert m.nickname == name and m.checksum_ok()
save.fix_checksum(s1, 1)
assert save.verify_checksums(slot) == []
open(dst, 'wb').write(save.raw)
