# Starting scales

Use the project's own tokens when it has them; these are defaults for a project that has none.

## Spacing (4 px grid)

4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128

| Between | Value |
|---|---|
| Inside a control | 4–12 |
| Rows of a list | 2–8 |
| A label and its group, two cards | 12–24 |
| Sections in an app | 32–64 |
| Sections on a landing page | 80–128 |

Row heights: 32 compact, 36 default, 40–44 touch. Page padding 24–32, content capped at 1440–1600.

## Type

| Use | Size / line height | Weight |
|---|---|---|
| Meta, counts, small labels | 12 / 16 | 400 |
| Captions, secondary text | 13–14 / 20 | 400 |
| Body, menu items | 14–15 / 20–22 | 400–500 |
| Card figures | 28–32 / 1 | 500, tabular |
| Page title | 28–36 / 1.15 | 500–600 |
| Hero headline | 48–72 / 1.05 (36–44 on phones) | 500–600 |

Letter spacing 0 below 16 px; display text from 40 px may go to −0.02 em, from 56 px to −0.03 em.

## Surfaces

A neutral ramp with very low saturation, tinted toward the product's world (warm, graphite or ink):
deepest surface, page, card, raised (inputs, active rows), hairline at 8 % of the text colour, and three text roles
(primary, secondary, muted). Muted text stays near 4.5 : 1 on its surface. Positive and negative colours are toned
to sit inside the ramp.

## Radius

| Element | Radius |
|---|---|
| Tag, keycap, small button | 4–6 |
| Input, row, button | 8–10 |
| Card | 12–16 |
| Panel, dialog | 16–20 |

Nested: inner = outer − padding, never below 4.

## Icons

One line set (lucide), 16 or 18 px, stroke 1.5–2, in the secondary or muted text colour, 8–10 px from the label.

## Motion

One curve, `cubic-bezier(0.22, 1, 0.36, 1)`. Hover and press 120–180 ms, menus 160–220 ms, entrances 300–500 ms,
stagger 40–60 ms for at most six items. Rise 6–12 px on enter, press scale 0.97–0.98. Transition colour, background,
border, opacity and transform only.
