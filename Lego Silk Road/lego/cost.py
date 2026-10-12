"""Cost model and sourcing split.  All prices are estimates (see catalog.py)."""

import math
from collections import Counter, defaultdict

from .catalog import BULK_PRICE_PER_PART, COLORS, PAB_PRICE, PARTS

RETAIL_PPP = (0.08, 0.12)        # target average price per part, USD
BL_SHIPPING_PER_STORE = 6.00     # typical domestic BrickLink shipping per order
BL_LOTS_PER_STORE = 40           # rough lots one well-stocked store can fill
PAB_SHIPPING = 5.99              # LEGO.com standard shipping below the free threshold
PAB_FREE_SHIPPING = 35.00


def bl_price(pid, color):
    return PARTS[pid].price * COLORS[color].price_mult


def pab_price(pid):
    return PAB_PRICE.get(pid)


def analyze(model, visible):
    lots = Counter((pl.part, pl.color) for pl in model.parts)
    hidden = Counter((pl.part, pl.color) for i, pl in enumerate(model.parts) if i not in visible)
    n_parts = len(model.parts)

    def bl_shipping(n_lots):
        return math.ceil(n_lots / BL_LOTS_PER_STORE) * BL_SHIPPING_PER_STORE if n_lots else 0.0

    def pab_shipping(subtotal):
        return 0.0 if subtotal == 0 or subtotal >= PAB_FREE_SHIPPING else PAB_SHIPPING

    all_bl_parts = sum(q * bl_price(p, c) for (p, c), q in lots.items())
    all_bl = all_bl_parts + bl_shipping(len(lots))
    all_pab_parts = sum(q * (pab_price(p) or bl_price(p, c)) for (p, c), q in lots.items())
    all_pab = all_pab_parts + pab_shipping(all_pab_parts)

    # Optimised split: concealed parts from bulk mixed-colour lots, every visible lot
    # from whichever of BrickLink / Pick a Brick is cheaper per unit.
    split = {"BrickLink": [], "Pick a Brick": [], "Bulk generic": []}
    for (p, c), q in sorted(lots.items()):
        h = hidden.get((p, c), 0)
        v = q - h
        cat = PARTS[p].category
        if h and PARTS[p].kind == "box" and cat in ("Brick", "Plate") and BULK_PRICE_PER_PART < bl_price(p, c):
            split["Bulk generic"].append((p, c, h, BULK_PRICE_PER_PART))
        else:
            v += h
        if v:
            bl, pab = bl_price(p, c), pab_price(p)
            if pab is not None and pab < bl:
                split["Pick a Brick"].append((p, c, v, pab))
            else:
                split["BrickLink"].append((p, c, v, bl))
    sub = {k: sum(q * u for _, _, q, u in v) for k, v in split.items()}
    bl_lots = len(split["BrickLink"])
    stores = math.ceil(bl_lots / BL_LOTS_PER_STORE) if bl_lots else 0
    ship = bl_shipping(bl_lots) + pab_shipping(sub["Pick a Brick"])
    optimised = sum(sub.values()) + ship

    # Part rationalisation: what the same tiled volume costs built only from 1 x 2
    # and 2 x 2 elements (the "small plates everywhere" baseline).
    naive_parts = naive_cost = 0.0
    tiled = defaultdict(int)
    for pl in model.parts:
        if getattr(pl, "spec", None) is not None:
            tiled[(model.specs[pl.spec]["kind"], pl.color)] += len(pl.cells)
    small = {"brick": ("3004", "3003"), "plate": ("3023", "3022"), "tile": ("3069b", "3068b")}
    actual_tiled_parts = sum(1 for pl in model.parts if getattr(pl, "spec", None) is not None)
    actual_tiled_cost = sum(bl_price(pl.part, pl.color) for pl in model.parts if getattr(pl, "spec", None) is not None)
    for (kind, color), cells in tiled.items():
        a, b = small[kind]
        # mix of one-third 2x2 (4 cells) and two-thirds 1x2 (2 cells) by area
        n = cells / 4 * (1 / 3) + cells / 2 * (2 / 3)
        naive_parts += n
        naive_cost += (cells / 4 * (1 / 3)) * bl_price(b, color) + (cells / 2 * (2 / 3)) * bl_price(a, color)

    groups = defaultdict(lambda: [0, 0.0])
    for pl in model.parts:
        g = pl.group.split("_")[0] if pl.group.startswith(("snot", "well", "pishtaq", "tower")) else pl.group
        groups[g][0] += 1
        groups[g][1] += bl_price(pl.part, pl.color)

    return {
        "parts": n_parts,
        "lots": len(lots),
        "hidden_parts": sum(hidden.values()),
        "all_bricklink": round(all_bl, 2),
        "all_bricklink_parts_only": round(all_bl_parts, 2),
        "all_pick_a_brick": round(all_pab, 2),
        "all_pick_a_brick_parts_only": round(all_pab_parts, 2),
        "optimised_parts_subtotals": {k: round(v, 2) for k, v in sub.items()},
        "optimised_shipping": round(ship, 2),
        "bricklink_stores_est": stores,
        "optimised_total": round(optimised, 2),
        "ppp_all_bricklink": round(all_bl / n_parts, 4),
        "ppp_parts_only_bricklink": round(all_bl_parts / n_parts, 4),
        "ppp_optimised": round(optimised / n_parts, 4),
        "retail_target_range": [round(n_parts * RETAIL_PPP[0], 2), round(n_parts * RETAIL_PPP[1], 2)],
        "within_retail_target": optimised <= n_parts * RETAIL_PPP[1],
        "rationalisation": {
            "tiled_parts_actual": actual_tiled_parts,
            "tiled_cost_actual": round(actual_tiled_cost, 2),
            "tiled_parts_small_only": round(naive_parts),
            "tiled_cost_small_only": round(naive_cost, 2),
        },
        "split": {k: [{"part": p, "color": c, "qty": q, "unit": round(u, 3)} for p, c, q, u in v]
                  for k, v in split.items()},
        "by_group": {g: {"parts": n, "bricklink_cost": round(cst, 2)}
                     for g, (n, cst) in sorted(groups.items(), key=lambda kv: -kv[1][1])},
    }
