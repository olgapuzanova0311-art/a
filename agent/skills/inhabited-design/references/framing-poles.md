# Framing poles (bankless)

Replaces the 200-entry `framing-bank.md`. Instead of selecting from a curated bank, the model **generates a fresh pool of ≈40 framings to the per-pole quotas below**, honoring the reach-into roster and the ban-list, then ms-samples 1 via the external Bash gate.

The quotas — especially the **scientific/instrument CAP** — the ban-list, and the reach-beyond mandate are the anti-attractor mechanism the curated bank used to provide. They are not optional: they are the part of the bank that was load-bearing. The 200 hand-written entries were not.

A framing is a **conceptual lens** — a 6–15-word sentence describing an abstract angle/register/constraint. NOT a reference name alone. NOT a one-word style label like "minimalist."

## Pole quotas (≈40 candidates total)

| Pole | Quota | Reach into (generate candidates from here) |
|---|---|---|
| Period (specific decade/moment) | 5 | a dated visual register: specific year + medium + place (mail-order catalogs, wire-service teleprinter output, magazine eras, ticket/coated stock) — never "vintage feel" |
| Practitioner-led (named figure) | 5 | a specific named person (film, illustration, editorial, photography, architecture) whose visual logic becomes the master — range across geography/era; NOT the graphic-design canon (see ban-list) |
| Subcultural / scene | 4 | a specific subculture's vernacular (nightlife signage, fanzine, trade scene, regional sport scoreboard) as the master register |
| Spatial / architectural | 4 | a specific place / building-type interior as logic (regional vernacular interiors, transit, religious, domestic) — reach non-Western |
| Cross-cultural / non-Western | 4 | a named non-Western tradition's compositional logic (manuscript, textile, signage, court painting) — geographic distance from the Western canon is the point |
| Material / medium | 4 | a substrate / ink / process as the master (risograph, intaglio, NCR carbon form, letterpress registration drift, thermal receipt, cyanotype) |
| Brief-canon-engaging | 4 | engage the brief's OWN positive attractor on its own terms (the canonical aesthetic for this domain, approached unironically and specifically) |
| Sensory / synesthetic | 3 | a sense (taste / sound / temperature / smell) as composition logic |
| Domestic / ritual | 3 | a household-scale ritual or document as the page grammar (ceremony order-of-operations, ledger, recipe card, order-of-service program) |
| Vernacular / found | 2 | street / amateur / accidental visual material (hand-painted signage, price tags, bulletin-board flyers) |
| **Scientific / instrument (CAP)** | **2** | **HARD CAP at 2/40 ≈ 5%.** strip-chart / telemetry / console / contour aesthetics. Do NOT exceed 2 — this pole is the documented collapse attractor (treehouse 5/5, ceramics 4–5/5 reaching for the scientific-cataloging register in v1–v3 smoke tests). |

Total ≈ 40. Scientific/instrument ≤ 2.

## Reach-beyond mandate

Within each pole, actively reach for **non-Western, non-mid-century-Western, contemporary-working, and regionally-specific** registers over design-history-textbook defaults. A pole filled with the obvious canonical examples is a generation failure. The lesson from typography VS applies here: *prohibition alone just promotes the next canonical face* — so reach into **territory**, don't merely avoid names. The reach-into column tells you where to look; the diversity has to come from genuinely ranging there.

## What NOT to generate (ban-list)

- **Swiss/Dutch modernist graphic-design canon named as a framing master**: no Karel Martens, Wim Crouwel, Massimo Vignelli, Josef Müller-Brockmann, Irma Boom, Stefan Sagmeister, David Carson, Herb Lubalin, Jan Tschichold, Herbert Bayer, Richard Lohse, Wolfgang Weingart, Catalogtree, Experimental Jetset. Already over-represented in the model's reach; the bank deliberately excluded them and so does this.
- **Generic single-word style labels** ("minimalism," "brutalism," "editorial print") — too vague to condition downstream steps.
- **The brief's exact category** ("energy-drink design," "Japanese-ceramics aesthetic") — defeats the purpose of escaping the canonical attractor.
- **More than 2 scientific/instrument framings** — the cap is structural, not advisory.

## Quota self-check (before sampling — mandatory)

Count your generated pool by pole. If scientific/instrument > 2, delete the excess and regenerate from an under-filled pole. Confirm the total is ≈40 and each pole is ≈ its quota. Record the per-pole counts in `sampling.md` so the distribution is auditable — this is the bankless analogue of the bank's structural quota, and the critic/analysis verifies it held.
