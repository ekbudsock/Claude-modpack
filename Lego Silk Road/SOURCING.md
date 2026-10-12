# Sourcing and cost strategy

All prices are estimates from curated catalogue data (typical BrickLink six-month averages for new parts, and LEGO Pick a Brick list prices), not live quotes. `parts.xml` in each build folder uploads straight to a BrickLink wanted list for current prices.

## Summary

| | Small | Medium | Large |
|---|---:|---:|---:|
| Parts | 124 | 281 | 676 |
| BrickLink lots (part + colour) | 26 | 45 | 57 |
| Concealed parts (any colour) | 0 | 1 | 8 |
| Retail target at $0.08–0.12/part | $9.92–$14.88 | $22.48–$33.72 | $54.08–$81.12 |
| All BrickLink, parts only | $10.95 | $26.92 | $76.36 |
| All BrickLink, incl. shipping | $16.95 | $38.92 | $88.36 |
| All Pick a Brick, incl. shipping | $22.84 | $40.86 | $113.15 |
| **Optimised split, incl. shipping** | **$16.95** | **$38.92** | **$88.36** |
| Price per part, parts only (BrickLink) | $0.088 | $0.096 | $0.113 |
| Price per part, optimised landed | $0.137 | $0.139 | $0.131 |
| Within $0.12/part target (landed) | no | no | no |
| All validation checks | pass | pass | pass |
| Running-bond joints staggered | 100.0% | 99.63% | 100.0% |

“Parts only” is the price of the bricks. “Landed” adds estimated shipping: about $6 per BrickLink store, with roughly 40 lots per store, plus Pick a Brick's $5.99 shipping when that order is under $35. LEGO retail sets average about $0.08–0.12 per part.

## Part rationalisation built into the design

These choices are made by the layout generator, not as an afterthought:

* **Largest element first.** Every course is tiled with the largest part that fits without breaking the running bond: 1 × 8 and 2 × 6 bricks, and 4 × N or 6 × N roof plates. The roof decks are a handful of big plates spanning wall to wall instead of a patchwork of small ones. The baseline below shows the same volume built from 1 × 2 and 2 × 2 elements only.
* **High-volume colours for big parts.** Large plates are all Tan, one of the most stocked colours. Dark Tan is used only for 1 × N and 2 × N trim plates and tiles, which are plentiful in that colour.
* **Common colour for the tilework.** The Persian blue panel uses Medium Azure, which is more widely stocked than Dark Turquoise or Dark Azure in 1 × 2 and 1 × 4 tiles.
* **Studs-up sand courtyard.** The baseplate's own studs are the desert floor. Only the path and the well apron are tiled, which saves tiling a 6 × 6 to 16 × 16 courtyard.
* **Hollow bastions** on the large build: 6 × 6 towers with a 2 × 2 void, capped by a plate spanning 2 studs.
* **Only current molds** (e.g. 3069b, 3070b, 3062b, 15254, 99781). Known retired versions are blocked by validation.

| | Small | Medium | Large |
|---|---:|---:|---:|
| Tiled parts, 1×2/2×2 only (baseline) | 135 | 454 | 1499 |
| Tiled parts, as generated | 85 | 224 | 579 |
| Cost baseline → generated | $7.16 → $6.87 | $23.51 → $20.37 | $78.60 → $60.19 |

## Small build

### Procurement split

| Channel | Lots | Parts | Subtotal | What goes here |
|---|---:|---:|---:|---|
| BrickLink | 26 | 124 | $10.95 | Every visible lot, all colour-critical: Dark Bluish Gray, Dark Tan, Light Bluish Gray, Reddish Brown, Tan, Trans-Light Blue |
| Pick a Brick | 0 | 0 | $0.00 | Elements where LEGO's own price beats the BrickLink average (none at these prices) |
| Bulk generic | 0 | 0 | $0.00 | Concealed structural core (any colour) (none at these prices) |
| Shipping (est., 1 BrickLink store(s)) | | | $6.00 | |
| **Total** | | **124** | **$16.95** | |

### Most expensive lots

| Part | Colour | Qty | Est. BrickLink |
|---|---|---:|---:|
| 3028 Plate 6 x 12 | Tan | 2 | $1.80 |
| 3004 Brick 1 x 2 | Tan | 29 | $1.45 |
| 3008 Brick 1 x 8 | Tan | 7 | $1.26 |
| 3460 Plate 1 x 8 | Dark Tan | 6 | $0.97 |
| 3003 Brick 2 x 2 | Tan | 9 | $0.63 |
| 3062b Brick, Round 1 x 1 Open Stud | Reddish Brown | 8 | $0.42 |
| 3005 Brick 1 x 1 | Tan | 8 | $0.40 |
| 3010 Brick 1 x 4 | Tan | 5 | $0.40 |
| 3023 Plate 1 x 2 | Dark Tan | 7 | $0.38 |
| 3009 Brick 1 x 6 | Tan | 3 | $0.36 |

### Cost by sub-assembly

| Sub-assembly | Parts | BrickLink cost |
|---|---:|---:|
| wall | 33 | $3.03 |
| foundation | 2 | $1.80 |
| well | 25 | $1.67 |
| tower | 26 | $1.43 |
| plinth | 11 | $0.99 |
| wall_cap | 6 | $0.68 |
| merlon | 9 | $0.45 |
| paving | 6 | $0.43 |

### Footprint and cost notes

* Parts alone come to $10.95 ($0.088/part), inside the retail range. Shipping ($6.00) is what pushes the landed cost $2.07 over the $14.88 ceiling.
* Drop one course from the four corner towers (they still clear the parapet): saves about $0.50.
* Combine with another order from the same store, or buy two sizes together: saves about $6.00.
* Applying these gets the landed cost to about $10.45 ($0.084/part).
* Price per part is a weak yardstick for this design, because consolidating into large parts raises it while lowering the total (see the rationalisation table). Compare totals, not price per part.

## Medium build

### Procurement split

| Channel | Lots | Parts | Subtotal | What goes here |
|---|---:|---:|---:|---|
| BrickLink | 45 | 281 | $26.92 | Every visible lot, all colour-critical: Dark Bluish Gray, Dark Tan, Light Bluish Gray, Medium Azure, Reddish Brown, Tan, Trans-Light Blue, White |
| Pick a Brick | 0 | 0 | $0.00 | Elements where LEGO's own price beats the BrickLink average (none at these prices) |
| Bulk generic | 0 | 0 | $0.00 | Concealed structural core (any colour) (none at these prices) |
| Shipping (est., 2 BrickLink store(s)) | | | $12.00 | |
| **Total** | | **281** | **$38.92** | |

### Most expensive lots

| Part | Colour | Qty | Est. BrickLink |
|---|---|---:|---:|
| 3008 Brick 1 x 8 | Tan | 17 | $3.06 |
| 3004 Brick 1 x 2 | Tan | 52 | $2.60 |
| 91405 Plate 16 x 16 | Tan | 1 | $2.50 |
| 3002 Brick 2 x 3 | Tan | 22 | $1.98 |
| 3622 Brick 1 x 3 | Tan | 27 | $1.89 |
| 3010 Brick 1 x 4 | Tan | 17 | $1.36 |
| 3460 Plate 1 x 8 | Dark Tan | 7 | $1.13 |
| 3035 Plate 4 x 8 | Tan | 3 | $1.05 |
| 3021 Plate 2 x 3 | Dark Tan | 11 | $1.04 |
| 3623 Plate 1 x 3 | Dark Tan | 15 | $1.01 |

### Cost by sub-assembly

| Sub-assembly | Parts | BrickLink cost |
|---|---:|---:|
| wall | 101 | $8.43 |
| tower | 36 | $2.53 |
| foundation | 1 | $2.50 |
| band | 27 | $2.13 |
| roof_deck | 7 | $2.08 |
| plinth | 23 | $2.05 |
| well | 25 | $1.67 |
| roof_trim | 12 | $1.03 |

### Footprint and cost notes

* Parts alone come to $26.92 ($0.096/part), inside the retail range. Shipping ($12.00) is what pushes the landed cost $5.20 over the $33.72 ceiling.
* Fill the whole wanted list from one large BrickLink store: saves about $6.00.
* Drop one course from the four corner towers (they still clear the parapet): saves about $0.89.
* Combine with another order from the same store, or buy two sizes together: saves about $6.00.
* Applying these gets the landed cost to about $26.03 ($0.093/part).
* Price per part is a weak yardstick for this design, because consolidating into large parts raises it while lowering the total (see the rationalisation table). Compare totals, not price per part.

## Large build

### Procurement split

| Channel | Lots | Parts | Subtotal | What goes here |
|---|---:|---:|---:|---|
| BrickLink | 57 | 676 | $76.36 | Every visible lot, all colour-critical: Dark Bluish Gray, Dark Tan, Light Bluish Gray, Medium Azure, Reddish Brown, Tan, Trans-Light Blue, White |
| Pick a Brick | 0 | 0 | $0.00 | Elements where LEGO's own price beats the BrickLink average (none at these prices) |
| Bulk generic | 0 | 0 | $0.00 | Concealed structural core (any colour) (none at these prices) |
| Shipping (est., 2 BrickLink store(s)) | | | $12.00 | |
| **Total** | | **676** | **$88.36** | |

### Most expensive lots

| Part | Colour | Qty | Est. BrickLink |
|---|---|---:|---:|
| 3811 Baseplate 32 x 32 | Tan | 1 | $9.00 |
| 2456 Brick 2 x 6 | Tan | 44 | $7.92 |
| 3001 Brick 2 x 4 | Tan | 56 | $5.60 |
| 3010 Brick 1 x 4 | Tan | 61 | $4.88 |
| 3008 Brick 1 x 8 | Tan | 24 | $4.32 |
| 3004 Brick 1 x 2 | Tan | 81 | $4.05 |
| 3005 Brick 1 x 1 | Tan | 55 | $2.75 |
| 3795 Plate 2 x 6 | Dark Tan | 16 | $2.59 |
| 3009 Brick 1 x 6 | Tan | 20 | $2.40 |
| 3622 Brick 1 x 3 | Tan | 34 | $2.38 |

### Cost by sub-assembly

| Sub-assembly | Parts | BrickLink cost |
|---|---:|---:|
| wall | 315 | $29.62 |
| foundation | 1 | $9.00 |
| tower | 83 | $7.47 |
| roof_deck | 24 | $6.58 |
| band | 65 | $5.91 |
| plinth | 59 | $5.56 |
| roof_trim | 22 | $2.11 |
| well | 25 | $1.67 |

### Footprint and cost notes

* Parts alone come to $76.36 ($0.113/part), inside the retail range. Shipping ($12.00) is what pushes the landed cost $7.24 over the $81.12 ceiling.
* Fill the whole wanted list from one large BrickLink store: saves about $6.00.
* Buy the baseplate used (typically about half price): saves about $4.50.
* Drop one course from the four corner towers (they still clear the parapet): saves about $2.61.
* Combine with another order from the same store, or buy two sizes together: saves about $6.00.
* Applying these gets the landed cost to about $69.25 ($0.102/part).
* Price per part is a weak yardstick for this design, because consolidating into large parts raises it while lowering the total (see the rationalisation table). Compare totals, not price per part.

## Channel strategy

| Channel | Use it for | Why |
|---|---|---|
| BrickLink | Every visible, colour-critical part: Tan walls and arches, Dark Tan trim, Medium Azure and White panel tiles, 99781 brackets, the baseplate | Lowest unit price on common parts, and every colour is available. Upload `parts.xml` and use Easy Buy to keep it to one or two stores. |
| LEGO Pick a Brick | Lots where LEGO's price beats the BrickLink average, and topping up a short BrickLink lot | Fixed prices with no store minimums. Only worth it above the free-shipping threshold. |
| Bulk generic (Classic boxes, bulk lots from Amazon or Walmart) | Parts nobody can see: inner cores of the double walls, tower hollows, plates under the roof deck | About $0.05 per part, but colours are random. The visibility analysis (a flood fill of outside air) found few or no fully concealed parts, because the walls are one or two studs thick and both faces show. |

Because the walls are thin and both faces are visible, almost the whole model is colour-critical. Bulk generic lots therefore don't save much here. The real savings come from part consolidation and from ordering from one or two BrickLink stores.

