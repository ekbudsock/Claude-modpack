"""Part and colour catalogue for the Lego Silk Road caravanserai.

Everything here is plain Python so the layout, validation, BOM and cost code
can run (and be tested) without Blender.

Units
-----
* 1 stud pitch = 8.0 mm (20 LDU)
* 1 plate      = 3.2 mm (8 LDU)
* 1 brick      = 9.6 mm (24 LDU) = 3 plates

Part IDs are BrickLink catalogue numbers, which match the LDraw file names for
every part used here (e.g. 3069b, 3062b).

Availability / pricing caveat
-----------------------------
``ACTIVE`` mold status, the colour availability table and the unit prices are
curated from public BrickLink / Pick a Brick catalogue data known at the time
of writing.  They are *not* fetched live.  Re-check prices before ordering.
"""

from dataclasses import dataclass, field

STUD = 8.0          # mm
PLATE = 3.2         # mm
BRICK = 9.6         # mm
STUD_D = 4.8        # mm
STUD_H = 1.7        # mm
GAP = 0.1           # mm total clearance between neighbouring sidewalls
INSET = GAP / 2.0   # mm each body face is pulled in by
BEVEL = 0.2         # mm micro-bevel on outer edges

# 5:2 SNOT relationship: two studs sideways == five plates stacked.
assert abs(2 * STUD - 5 * PLATE) < 1e-9


@dataclass(frozen=True)
class Color:
    bl_id: int
    name: str
    hex: str            # LEGO official sRGB value
    price_mult: float   # relative BrickLink price vs. Tan (1.0)
    transparent: bool = False


# BrickLink colour IDs.  Hex values are LEGO's published sRGB values.
COLORS = {
    "White":             Color(1,   "White",             "#F4F4F4", 0.90),
    "Tan":               Color(2,   "Tan",               "#D7C599", 1.00),
    "Dark Tan":          Color(69,  "Dark Tan",          "#958A73", 1.35),
    "Reddish Brown":     Color(88,  "Reddish Brown",     "#694027", 1.05),
    "Dark Bluish Gray":  Color(85,  "Dark Bluish Gray",  "#635F62", 0.85),
    "Light Bluish Gray": Color(86,  "Light Bluish Gray", "#A3A2A4", 0.85),
    "Medium Azure":      Color(156, "Medium Azure",      "#36AEBF", 1.25),
    "Trans-Light Blue":  Color(15,  "Trans-Light Blue",  "#AEEFEC", 1.20, transparent=True),
    "Black":             Color(11,  "Black",             "#1B2A34", 0.90),
}


@dataclass(frozen=True)
class Part:
    id: str
    name: str
    category: str            # Brick | Plate | Tile | Slope | Bracket | Modified
    kind: str                # mesh family: box | slope | arch | round | bracket | baseplate
    w: int                   # studs along local X
    d: int                   # studs along local Y
    h: int                   # height in plates
    price: float             # est. BrickLink avg new price, USD, in Tan
    studs: bool = True       # studs on top across the footprint
    stud_cells: tuple = None  # override: local (x, y) cells carrying studs
    bottom_cells: tuple = None  # override: local cells that accept studs below
    active: bool = True      # current, widely available mold
    extra: dict = field(default_factory=dict, hash=False, compare=False)

    def cells(self):
        return [(x, y) for x in range(self.w) for y in range(self.d)]

    def top_cells(self):
        if not self.studs:
            return []
        return list(self.stud_cells) if self.stud_cells is not None else self.cells()

    def base_cells(self):
        return list(self.bottom_cells) if self.bottom_cells is not None else self.cells()


def _p(*a, **k):
    part = Part(*a, **k)
    PARTS[part.id] = part
    return part


PARTS = {}

# --- Bricks -----------------------------------------------------------------
_p("3005", "Brick 1 x 1", "Brick", "box", 1, 1, 3, 0.05)
_p("3004", "Brick 1 x 2", "Brick", "box", 2, 1, 3, 0.05)
_p("3622", "Brick 1 x 3", "Brick", "box", 3, 1, 3, 0.07)
_p("3010", "Brick 1 x 4", "Brick", "box", 4, 1, 3, 0.08)
_p("3009", "Brick 1 x 6", "Brick", "box", 6, 1, 3, 0.12)
_p("3008", "Brick 1 x 8", "Brick", "box", 8, 1, 3, 0.18)
_p("3003", "Brick 2 x 2", "Brick", "box", 2, 2, 3, 0.07)
_p("3002", "Brick 2 x 3", "Brick", "box", 3, 2, 3, 0.09)
_p("3001", "Brick 2 x 4", "Brick", "box", 4, 2, 3, 0.10)
_p("2456", "Brick 2 x 6", "Brick", "box", 6, 2, 3, 0.18)
_p("3062b", "Brick, Round 1 x 1 Open Stud", "Brick", "round", 1, 1, 3, 0.05)
# Arches: only the two legs sit on studs below; studs run the full length on top.
_p("3659", "Brick, Arch 1 x 4", "Brick", "arch", 4, 1, 3, 0.12,
   bottom_cells=((0, 0), (3, 0)), extra={"span": 2, "spring": 0.0, "crown": 1.6})
_p("15254", "Brick, Arch 1 x 6 x 2", "Brick", "arch", 6, 1, 6, 0.35,
   bottom_cells=((0, 0), (5, 0)), extra={"span": 4, "spring": 0.8, "crown": 2.4})

# --- Plates -----------------------------------------------------------------
for pid, w, d, price in [
    ("3024", 1, 1, 0.03), ("3023", 2, 1, 0.04), ("3623", 3, 1, 0.05),
    ("3710", 4, 1, 0.06), ("3666", 6, 1, 0.08), ("3460", 8, 1, 0.12),
    ("3022", 2, 2, 0.05), ("3021", 3, 2, 0.07), ("3020", 4, 2, 0.08),
    ("3795", 6, 2, 0.12), ("3034", 8, 2, 0.15), ("3832", 10, 2, 0.20),
    ("3031", 4, 4, 0.20), ("3032", 6, 4, 0.25), ("3035", 8, 4, 0.35),
    ("3030", 10, 4, 0.45), ("3958", 6, 6, 0.40), ("3036", 8, 6, 0.55),
    ("3033", 10, 6, 0.70), ("3028", 12, 6, 0.90), ("41539", 8, 8, 0.85),
    ("91405", 16, 16, 2.50),
]:
    _p(pid, f"Plate {d} x {w}", "Plate", "box", w, d, 1, price)
_p("3811", "Baseplate 32 x 32", "Plate", "baseplate", 32, 32, 1, 9.00)

# --- Tiles ------------------------------------------------------------------
for pid, w, d, price in [
    ("3070b", 1, 1, 0.04), ("3069b", 2, 1, 0.04), ("63864", 3, 1, 0.07),
    ("2431", 4, 1, 0.08), ("6636", 6, 1, 0.12), ("4162", 8, 1, 0.18),
    ("3068b", 2, 2, 0.07), ("87079", 4, 2, 0.18),
]:
    _p(pid, f"Tile {d} x {w}", "Tile", "box", w, d, 1, price, studs=False)
_p("98138", "Tile, Round 1 x 1", "Tile", "round", 1, 1, 1, 0.05, studs=False)

# --- Slopes -----------------------------------------------------------------
# High edge at local +Y; studs only on the top (rear) row.
_p("3039", "Slope 45 2 x 2", "Slope", "slope", 2, 2, 3, 0.08,
   stud_cells=((0, 1), (1, 1)))

# --- Brackets (SNOT) --------------------------------------------------------
# 1 x 2 base plate; a 1 x 2 vertical plate hangs off the local -Y edge with
# its bottom flush with the base, studs facing -Y at 4.0 mm above the base.
_p("99781", "Bracket 1 x 2 - 1 x 2", "Bracket", "bracket", 2, 1, 1, 0.08)

# Retired / obsolete molds that must never appear in a BOM.
OBSOLETE = {
    "3068a": "Tile 2x2 without groove",
    "3069a": "Tile 1x2 without groove",
    "3070a": "Tile 1x1 without groove",
    "3062a": "Round brick 1x1 solid stud",
    "4589": "Cone 1x1 without top groove",
    "3794a": "Jumper plate without groove",
    "2453a": "Brick 1x1x5 solid stud",
}

# Part/colour combinations that are in current production and widely stocked
# (hundreds of BrickLink lots).  The layout generator may only draw from these.
_STD_BRICKS = {"3005", "3004", "3622", "3010", "3009", "3008", "3003", "3002", "3001", "2456"}
_SMALL_PLATES = {"3024", "3023", "3623", "3710", "3666", "3460", "3022", "3021", "3020", "3795", "3034"}
_ALL_PLATES = _SMALL_PLATES | {"3832", "3031", "3032", "3035", "3030", "3958", "3036", "3033", "3028", "41539"}
_TILES = {"3070b", "3069b", "63864", "2431", "6636", "4162", "3068b", "87079"}

AVAILABLE = {
    "Tan": _STD_BRICKS | _ALL_PLATES | _TILES | {"3659", "15254", "3062b", "99781", "91405", "3811"},
    "Dark Tan": _SMALL_PLATES | {"3070b", "3069b", "2431", "3068b", "3005", "3004", "3010"},
    "Reddish Brown": {"3062b", "3031", "3039", "3004", "3010", "3023", "3710", "3069b"},
    "Dark Bluish Gray": _STD_BRICKS | _SMALL_PLATES | _TILES,
    "Light Bluish Gray": _STD_BRICKS | _SMALL_PLATES | _TILES,
    "Medium Azure": {"3020", "3069b", "2431", "3068b", "3023", "3004"},
    "White": {"3069b", "2431", "3068b", "3070b", "3020"},
    "Trans-Light Blue": {"98138"},
    "Black": _STD_BRICKS | _SMALL_PLATES | _TILES,
}


def is_available(part_id, color):
    return part_id in AVAILABLE.get(color, set())


def sizes_for(kind, color):
    """(part_id, w, d) for every tiling element of one height class in a colour,
    largest area first."""
    out = []
    for p in PARTS.values():
        if not is_available(p.id, color) or p.kind != "box":
            continue
        if kind == "brick" and p.category == "Brick" and p.h == 3:
            out.append(p)
        elif kind == "plate" and p.category == "Plate" and p.id != "91405":
            out.append(p)
        elif kind == "tile" and p.category == "Tile":
            out.append(p)
    out.sort(key=lambda p: (-(p.w * p.d), p.id))
    return out


# --- Retail sourcing price models (USD per part, Tan baseline) --------------
# Pick a Brick prices are per element; most basic elements sit in the
# "Bestseller" tier.  Values are typical, not quoted.
PAB_PRICE = {
    "3005": 0.10, "3004": 0.10, "3622": 0.13, "3010": 0.15, "3009": 0.20, "3008": 0.25,
    "3003": 0.12, "3002": 0.16, "3001": 0.18, "2456": 0.26,
    "3024": 0.06, "3023": 0.07, "3623": 0.09, "3710": 0.10, "3666": 0.14, "3460": 0.18,
    "3022": 0.10, "3021": 0.12, "3020": 0.14, "3795": 0.18, "3034": 0.22, "3832": 0.28,
    "3031": 0.28, "3032": 0.36, "3035": 0.45, "3030": 0.55, "3958": 0.50, "3036": 0.65,
    "3033": 0.80, "3028": 1.05, "41539": 0.95, "91405": 2.90, "3811": 10.0,
    "3070b": 0.07, "3069b": 0.08, "63864": 0.11, "2431": 0.12, "6636": 0.16, "4162": 0.22,
    "3068b": 0.10, "87079": 0.22, "98138": 0.07, "3062b": 0.08,
    "3659": 0.18, "15254": 0.40, "3039": 0.14, "99781": 0.12,
}
# Bulk generic lots (LEGO Classic boxes / bulk bricks from big-box retail):
# mixed colours, so only useful for parts nobody sees.
BULK_PRICE_PER_PART = 0.055
