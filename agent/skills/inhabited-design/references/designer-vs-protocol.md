# Designer VS protocol (bankless — generate to discipline rosters)

Step 5 of the pipeline samples one practitioner whose voice and discipline become the Designer persona for the build. The persona is generated in Step 12 from `designer-persona-template.md` using the sampled practitioner as the voice anchor. The sampled practitioner also contributes one representative work to the 7-anchor inspiration bank.

## The 10×2 bankless pool

The 20-candidate pool is composed as **2 live-generated candidates per discipline × 10 disciplines**. There is no curated practitioner bank — candidates are generated against the per-discipline reach-into rosters in `designer-disciplines.md`. Per discipline:

- **Slot A — framing-fit:** the strongest fit whose voice carries the framing (may be well-known if genuinely apt).
- **Slot B — non-canon counter-weight:** an under-represented / non-Western / contemporary-working practitioner from the reach-into roster. This slot is the structural counter-weight to the model's canon-reaching reflex — the job the old bank slot did, now carried by the roster + ban-list + reach-beyond mandate rather than curated entries.

### The 10 disciplines

Graphic design / Type design / Industrial design / Architecture / Fine art / Photography / Fashion design / Film + cinematic / Digital + UX + interactive / Craft + vernacular + regional.

These are stable; do not invent additional disciplines. They mirror `designer-disciplines.md`.

## Generation procedure

### Step 1 — Read the discipline rosters

`Read` `designer-disciplines.md` in full. The reach-into rosters, the graphic-design ban-list, and the reach-beyond mandate are the anti-canon mechanism — honor them exactly.

### Step 2 — Generate 2 candidates per discipline

For each of the 10 disciplines, generate a **framing-fit** candidate (Slot A) and a **non-canon counter-weight** candidate (Slot B) from that discipline's reach-into territory. Each candidate is a *real practitioner* (name, discipline, era, signature work) — not a description. Verbalize a one-line reason per candidate: why their voice fits or productively tensions the framing.

- **Graphic design:** BOTH slots must avoid the Swiss/Dutch ban-list (the graphic anti-canon is absolute for this discipline).
- **Reach-beyond:** across the 20, non-Western / contemporary-working / women practitioners should be over-represented relative to textbook coverage. A pool that is mostly mid-century Western men is a generation failure — regenerate the offending Slot-B candidates.

Tag each candidate `discipline` + `slot` (`fit` | `noncanon`). 20 candidates total.

## Brief-fitness gate

Each of the 20 candidates passes the **conditioning-fitness test**:

> *"If this practitioner were the Designer persona for this brief + framing, would the result be coherently conditioned on the framing — or would the practitioner's voice fight the framing so hard the build becomes generic?"*

A "can the practitioner's voice carry this framing" gate, not a "would I personally pick them" gate. A practitioner whose discipline is so far from the brief that the framing collapses fails. A practitioner whose voice productively tensions against the framing passes.

For each FAIL: regenerate another candidate from the **same discipline + same slot** (a fit fail → regenerate a fit candidate; a noncanon fail → regenerate from the roster). Cap at **3 replacement iterations per slot**. If a slot still fails, keep the best available and flag in the audit trail.

Record each round in `sampling.md` under `## Designer fitness rounds`:

```
Round 1:
  1.  [graphic / fit]     Eiko Ishioka → PASS
  2.  [graphic / noncanon] Reza Abedini → PASS (Persian-Latin poster carries the framing)
  ...
  11. [craft / noncanon]  Magdalene Odundo → FAIL (vessel craft doesn't carry a Futurist graphic brief)
  Replacement 11a: [craft / noncanon] Enzo Mari → PASS
  ...
```

Once all 20 PASS, sampling proceeds.

## Sample 1 uniformly

ms-sample 1 from the 20 PASSing candidates via the external gate (see `sampling-protocol.md` §The external sampling gate). The resolved practitioner is the locked Designer for the build.

## Present + confirm

Present the full 20-entry pool (with discipline + slot tags), Bash command + stdout, chosen practitioner, and a one-paragraph justification of why their voice + discipline serves this brief + framing.

`new options` in this protocol: discard the 20-pool entirely and re-generate both slots across all disciplines for the brief + framing. Other actions standard per `sampling-protocol.md` §The present + confirm pattern.

## Status-write

After locking the Designer, `Edit` `pipeline_status.md` row 5 → `done`, with `Artifact` = `sampling.md §Designer locked`. Update `Last updated`.

## Worked example

Brief: SOC analyst dashboard. Framing: "Mark Coleran cinematic HUDs from *Children of Men*, applied to a Marisol-Vega-tier-2-analyst console."

### The 20-pool (fit + noncanon per discipline)

| # | Discipline | Slot A (fit) | Slot B (noncanon) |
|---|---|---|---|
| 1 | graphic | Annie Atkins (film prop graphics) | Reza Abedini (Persian-Latin poster) |
| 2 | type | Matthew Carter (screen legibility) | Nadine Chahine (Arabic/Latin) |
| 3 | industrial | Konstantin Grcic (Chair_One) | Oki Sato / Nendo |
| 4 | architecture | Jean Prouvé | Francis Kéré |
| 5 | fine art | Olafur Eliasson | El Anatsui |
| 6 | photography | Wolfgang Tillmans | Daido Moriyama |
| 7 | fashion | Hussein Chalayan | Grace Wales Bonner |
| 8 | film | Mark Coleran (the framing anchor) | Mati Diop |
| 9 | digital | Tobias Frere-Jones | Devine Lu Linvega |
| 10 | craft | Maarten Baas | Magdalene Odundo |

### Brief-fitness gate

Round 1: 19/20 PASS. `[craft / noncanon] Magdalene Odundo` fails (burnished-vessel craft doesn't map to a cinematic HUD register). Replacement → **Enzo Mari** (open-source/militant-simplicity reads onto console rationalism). PASS. All 20 pass.

### Bash ms-sample

```
SEED=1779608451337
PICKS=[8]
```

Pool index 8 → `[film / fit] Mark Coleran`.

### Locked Designer

**Mark Coleran** (film / UK). The persona is generated in his voice: fictional-UI / cinematic-HUD discipline. The inspiration bank includes one representative HUD still from his work.
