"""Markdown tables for SOURCING.md, generated from builds/<size>/cost.json."""

import json
import os

from .catalog import COLORS, PARTS

SIZES = ("small", "medium", "large")


def _load(builds, size, name):
    with open(os.path.join(builds, size, name)) as f:
        return json.load(f)


def money(v):
    return f"${v:,.2f}"


def summary_table(builds):
    rows = ["| | Small | Medium | Large |", "|---|---:|---:|---:|"]
    data = {s: _load(builds, s, "cost.json") for s in SIZES}
    val = {s: _load(builds, s, "validation.json") for s in SIZES}

    def line(label, fn):
        rows.append(f"| {label} | " + " | ".join(fn(s) for s in SIZES) + " |")

    line("Parts", lambda s: f"{data[s]['parts']:,}")
    line("BrickLink lots (part + colour)", lambda s: str(data[s]["lots"]))
    line("Concealed parts (any colour)", lambda s: str(data[s]["hidden_parts"]))
    line("Retail target at $0.08–0.12/part", lambda s: f"{money(data[s]['retail_target_range'][0])}–{money(data[s]['retail_target_range'][1])}")
    line("All BrickLink, parts only", lambda s: money(data[s]["all_bricklink_parts_only"]))
    line("All BrickLink, incl. shipping", lambda s: money(data[s]["all_bricklink"]))
    line("All Pick a Brick, incl. shipping", lambda s: money(data[s]["all_pick_a_brick"]))
    line("**Optimised split, incl. shipping**", lambda s: f"**{money(data[s]['optimised_total'])}**")
    line("Price per part, parts only (BrickLink)", lambda s: f"${data[s]['ppp_parts_only_bricklink']:.3f}")
    line("Price per part, optimised landed", lambda s: f"${data[s]['ppp_optimised']:.3f}")
    line("Within $0.12/part target (landed)", lambda s: "yes" if data[s]["within_retail_target"] else "no")
    line("All validation checks", lambda s: "pass" if val[s]["passed"] else "FAIL")
    line("Running-bond joints staggered", lambda s: f"{val[s]['running_bond']['staggered_pct']}%")
    return "\n".join(rows)


def split_table(builds, size):
    d = _load(builds, size, "cost.json")
    rows = ["| Channel | Lots | Parts | Subtotal | What goes here |", "|---|---:|---:|---:|---|"]
    what = {
        "BrickLink": "Colour-critical exterior parts: Tan walls, arches, Dark Tan trim, Medium Azure tilework, brackets, baseplate",
        "Pick a Brick": "Elements where LEGO's own price beats the BrickLink average",
        "Bulk generic": "Concealed structural core (any colour)",
    }
    for ch, items in d["split"].items():
        desc = what[ch]
        if ch == "BrickLink" and items:
            cols = sorted({i["color"] for i in items})
            desc = "Every visible lot, all colour-critical: " + ", ".join(cols)
        elif not items:
            desc += " (none at these prices)"
        rows.append(f"| {ch} | {len(items)} | {sum(i['qty'] for i in items)} | "
                    f"{money(d['optimised_parts_subtotals'][ch])} | {desc} |")
    rows.append(f"| Shipping (est., {d['bricklink_stores_est']} BrickLink store(s)) | | | {money(d['optimised_shipping'])} | |")
    rows.append(f"| **Total** | | **{d['parts']}** | **{money(d['optimised_total'])}** | |")
    return "\n".join(rows)


def group_table(builds, size, top=8):
    d = _load(builds, size, "cost.json")
    rows = ["| Sub-assembly | Parts | BrickLink cost |", "|---|---:|---:|"]
    for g, v in list(d["by_group"].items())[:top]:
        rows.append(f"| {g} | {v['parts']} | {money(v['bricklink_cost'])} |")
    return "\n".join(rows)


def rationalisation_table(builds):
    rows = ["| | Small | Medium | Large |", "|---|---:|---:|---:|"]
    data = {s: _load(builds, s, "cost.json")["rationalisation"] for s in SIZES}
    rows.append("| Tiled parts, 1×2/2×2 only (baseline) | " + " | ".join(str(data[s]["tiled_parts_small_only"]) for s in SIZES) + " |")
    rows.append("| Tiled parts, as generated | " + " | ".join(str(data[s]["tiled_parts_actual"]) for s in SIZES) + " |")
    rows.append("| Cost baseline → generated | " + " | ".join(
        f"{money(data[s]['tiled_cost_small_only'])} → {money(data[s]['tiled_cost_actual'])}" for s in SIZES) + " |")
    return "\n".join(rows)


def top_lots(builds, size, n=10):
    import csv
    with open(os.path.join(builds, size, "bom.csv")) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["cost"] = PARTS[r["Part_ID"]].price * COLORS[r["Color_Name"]].price_mult * int(r["Quantity"])
    rows.sort(key=lambda r: -r["cost"])
    out = ["| Part | Colour | Qty | Est. BrickLink |", "|---|---|---:|---:|"]
    for r in rows[:n]:
        out.append(f"| {r['Part_ID']} {r['Part_Name']} | {r['Color_Name']} | {r['Quantity']} | {money(r['cost'])} |")
    return "\n".join(out)


def _recommendations(builds, size):
    d = _load(builds, size, "cost.json")
    n = d["parts"]
    ceiling = n * 0.12
    groups = d["by_group"]
    out = []
    if d["within_retail_target"]:
        out.append(f"Landed cost {money(d['optimised_total'])} is inside the $0.12/part ceiling "
                   f"({money(ceiling)}); no footprint change is needed.")
        return out
    over = d["optimised_total"] - ceiling
    out.append(f"Parts alone come to {money(d['all_bricklink_parts_only'])} "
               f"(${d['ppp_parts_only_bricklink']:.3f}/part), inside the retail range. Shipping "
               f"({money(d['optimised_shipping'])}) is what pushes the landed cost "
               f"{money(over)} over the {money(ceiling)} ceiling.")
    levers = []
    if d["bricklink_stores_est"] > 1:
        levers.append(("Fill the whole wanted list from one large BrickLink store", 6.0))
    found = groups.get("foundation", {}).get("bricklink_cost", 0)
    if found >= 5:
        levers.append(("Buy the baseplate used (typically about half price)", found * 0.5))
    tower = groups.get("tower", {}).get("bricklink_cost", 0)
    if tower:
        levers.append(("Drop one course from the four corner towers (they still clear the parapet)", tower * 0.35))
    levers.append(("Combine with another order from the same store, or buy two sizes together",
                   min(6.0, d["optimised_shipping"])))
    saved = 0.0
    for text, amount in levers:
        saved += amount
        out.append(f"{text}: saves about {money(amount)}.")
    out.append(f"Applying these gets the landed cost to about {money(d['optimised_total'] - saved)} "
               f"(${(d['optimised_total'] - saved) / n:.3f}/part).")
    out.append("Price per part is a weak yardstick for this design, because consolidating into "
               "large parts raises it while lowering the total (see the rationalisation table). "
               "Compare totals, not price per part.")
    return out


def write_sourcing(builds, path):
    md = []
    md.append("# Sourcing and cost strategy\n")
    md.append("All prices are estimates from curated catalogue data (typical BrickLink "
              "six-month averages for new parts, and LEGO Pick a Brick list prices), "
              "not live quotes. `parts.xml` in each build folder uploads straight to a "
              "BrickLink wanted list for current prices.\n")
    md.append("## Summary\n")
    md.append(summary_table(builds) + "\n")
    md.append("“Parts only” is the price of the bricks. “Landed” adds estimated shipping: "
              "about $6 per BrickLink store, with roughly 40 lots per store, plus "
              "Pick a Brick's $5.99 shipping when that order is under $35. LEGO retail "
              "sets average about $0.08–0.12 per part.\n")
    md.append("## Part rationalisation built into the design\n")
    md.append("These choices are made by the layout generator, not as an afterthought:\n")
    md.append("* **Largest element first.** Every course is tiled with the largest part that fits "
              "without breaking the running bond: 1 × 8 and 2 × 6 bricks, and 4 × N or 6 × N roof "
              "plates. The roof decks are a handful of big plates spanning wall to wall instead of "
              "a patchwork of small ones. The baseline below shows the same volume built from "
              "1 × 2 and 2 × 2 elements only.")
    md.append("* **High-volume colours for big parts.** Large plates are all Tan, one of the most "
              "stocked colours. Dark Tan is used only for 1 × N and 2 × N trim plates and tiles, "
              "which are plentiful in that colour.")
    md.append("* **Common colour for the tilework.** The Persian blue panel uses Medium Azure, which "
              "is more widely stocked than Dark Turquoise or Dark Azure in 1 × 2 and 1 × 4 tiles.")
    md.append("* **Studs-up sand courtyard.** The baseplate's own studs are the desert floor. Only "
              "the path and the well apron are tiled, which saves tiling a 6 × 6 to 16 × 16 courtyard.")
    md.append("* **Hollow bastions** on the large build: 6 × 6 towers with a 2 × 2 void, capped by "
              "a plate spanning 2 studs.")
    md.append("* **Only current molds** (e.g. 3069b, 3070b, 3062b, 15254, 99781). Known retired "
              "versions are blocked by validation.\n")
    md.append(rationalisation_table(builds) + "\n")
    for size in SIZES:
        md.append(f"## {size.capitalize()} build\n")
        md.append("### Procurement split\n")
        md.append(split_table(builds, size) + "\n")
        md.append("### Most expensive lots\n")
        md.append(top_lots(builds, size) + "\n")
        md.append("### Cost by sub-assembly\n")
        md.append(group_table(builds, size) + "\n")
        md.append("### Footprint and cost notes\n")
        md.extend(f"* {r}" for r in _recommendations(builds, size))
        md.append("")
    md.append("## Channel strategy\n")
    md.append("| Channel | Use it for | Why |")
    md.append("|---|---|---|")
    md.append("| BrickLink | Every visible, colour-critical part: Tan walls and arches, Dark Tan trim, "
              "Medium Azure and White panel tiles, 99781 brackets, the baseplate | Lowest unit price "
              "on common parts, and every colour is available. Upload `parts.xml` and use "
              "Easy Buy to keep it to one or two stores. |")
    md.append("| LEGO Pick a Brick | Lots where LEGO's price beats the BrickLink average, and "
              "topping up a short BrickLink lot | Fixed prices with no store minimums. Only "
              "worth it above the free-shipping threshold. |")
    md.append("| Bulk generic (Classic boxes, bulk lots from Amazon or Walmart) | Parts nobody can "
              "see: inner cores of the double walls, tower hollows, plates under the roof deck "
              "| About $0.05 per part, but colours are random. The visibility analysis "
              "(a flood fill of outside air) found few or no fully concealed parts, because "
              "the walls are one or two studs thick and both faces show. |")
    md.append("")
    md.append("Because the walls are thin and both faces are visible, almost the whole model "
              "is colour-critical. Bulk generic lots therefore don't save much here. The real "
              "savings come from part consolidation and from ordering from one or two BrickLink "
              "stores.\n")
    with open(path, "w") as f:
        f.write("\n".join(md) + "\n")
