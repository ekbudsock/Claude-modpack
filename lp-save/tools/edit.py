import struct, sys
sys.path.insert(0, 'tools')
from gen3save import Save, BoxMon
src, dst = sys.argv[1], sys.argv[2]
save = Save(open(src, 'rb').read())
slot = save.latest_slot(); secs = save.slot_sections(slot); s1 = secs[1]
def party(i): return BoxMon(save.raw, s1 + 0x238 + i * 100)
# (party index, expected species, move slot, expected old move, new move, new PP)
edits = [(0, 148, 0, 97, 21, 20),    # Dragonair: Agility -> Slam
         (4, 47, 0, 286, 185, 20)]   # Zoroark: Imprison -> Faint Attack
for idx, species, mslot, old, new, pp in edits:
    m = party(idx)
    assert m.species() == species and m.moves()[0][mslot] == old, (idx, m.species(), m.moves())
    assert (m.pp_bonuses() >> (2 * mslot)) & 3 == 0  # no PP Ups on that slot, so max PP is the base PP
    m.set_move(mslot, new, pp)
    assert m.checksum_ok()
save.fix_checksum(s1, 1)
assert save.verify_checksums(slot) == []
open(dst, 'wb').write(save.raw)
