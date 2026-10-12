"""Bill of materials: bom.csv and a BrickLink wanted-list XML (parts.xml)."""

import csv
from collections import Counter
from xml.sax.saxutils import escape

from .catalog import COLORS, PARTS

CSV_COLUMNS = ["Part_ID", "Part_Name", "Color_ID", "Color_Name", "Quantity", "Category"]


def bom_rows(model):
    counts = Counter((pl.part, pl.color) for pl in model.parts)
    rows = []
    for (pid, color), qty in counts.items():
        p, c = PARTS[pid], COLORS[color]
        rows.append({"Part_ID": pid, "Part_Name": p.name, "Color_ID": c.bl_id,
                     "Color_Name": c.name, "Quantity": qty, "Category": p.category})
    order = {"Plate": 0, "Brick": 1, "Tile": 2, "Slope": 3, "Bracket": 4, "Modified": 5}
    rows.sort(key=lambda r: (order[r["Category"]], r["Color_Name"], r["Part_ID"]))
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def write_bricklink_xml(rows, path):
    """BrickLink wanted-list upload format (Wanted > Upload > XML)."""
    lines = ["<INVENTORY>"]
    for r in rows:
        lines += [
            "  <ITEM>",
            "    <ITEMTYPE>P</ITEMTYPE>",
            f"    <ITEMID>{escape(r['Part_ID'])}</ITEMID>",
            f"    <COLOR>{r['Color_ID']}</COLOR>",
            f"    <MINQTY>{r['Quantity']}</MINQTY>",
            "    <CONDITION>N</CONDITION>",
            "    <NOTIFY>N</NOTIFY>",
            "  </ITEM>",
        ]
    lines.append("</INVENTORY>")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
