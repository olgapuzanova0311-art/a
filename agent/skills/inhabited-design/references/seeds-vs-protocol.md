# Seeds VS protocol

Step 6 of the pipeline samples two **framing-conditioned visual references** that anchor the inspiration bank. Seeds are the concrete artifacts a Designer would pin to a wall and refer to repeatedly while building — not abstract directions, not mood-board atmospheres. The framing is the angle; the seeds are the artifacts that demonstrate the angle in real, specific, citable form.

Both sampled seeds enter the 7-anchor inspiration bank alongside the designer signature work (Step 5), the two sampled competitors (Step 8), and the two domain-research references (Step 9). The Designer studies them before any design code is written.

Seeds are framing-conditioned: each must extend the framing concretely, not just match its mood. A seed for a "1987 FT pink-paper" framing is not "any 1980s magazine"; it is a specific FT Lex column from 1987 or an actual Hammond Atlas economic plate from that decade. Concrete and citable.

## The 10 artifact-type categories

One type-forced category per slot, four candidates per category = 40-pool. Categories are *artifact origin types*, not aesthetic labels — they apply across any framing.

### 1. Historical artifact
A specific period print, document, signage, or printed matter — dated, identifiable, reproducible. Not "vintage feel"; a *specific* artifact from a *specific* moment.
Examples: 1962 Pan Am ticket jacket; 1923 Berliner Illustrierte Zeitung cover; 1665 Athanasius Kircher *Mundus Subterraneus* plate; 1987 Financial Times Lex column.

### 2. Contemporary practitioner's work
A specific piece of work by a living or recently active practitioner — not the body of work, a specific *piece*. Citable: poster, publication, film still, website, packaging.
Examples: Mark Porter's 2005 Guardian redesign cover; Karel Martens's Werkplaats Typografie postcards 2015; Christoph Niemann's *Sunday Sketches* page 47.

### 3. Physical object / product
A non-designed (or industrially designed) physical artifact — the *thing itself*, not an image of it. The seed is the object's physical surface, not a marketing photograph.
Examples: Casio F-91W watch face; Bang & Olufsen Beomaster 6000 front panel; Trimble Pathfinder GPS receiver; Patek Philippe specimen literature folder.

### 4. Document / procedural
A form, manual, technical spec, ticket, receipt, ledger, or similar bureaucratic / procedural artifact. The thing's job is to record or transact.
Examples: NOAA aviation METAR string; Costa Rican customs declaration card; Bundesbahn Kursbuch timetable; kiln-firing log strip; polysomnography sleep-study trace.

### 5. Interface / instrument
A software UI, hardware faceplate, dashboard, gauge cluster, scope, or instrument-control surface. Live or historical.
Examples: Bloomberg Terminal Level-2 book pre-2016; Tektronix 1740 waveform monitor faceplate; CERN ALEPH event display; Grundig Satellit 2100 tuning dial.

### 6. Institutional production
A document, exhibition catalog, signage system, or printed matter produced by a museum, archive, library, or government / institutional body. The institutional voice is the asset.
Examples: Smithsonian Tropical Research Institute publication; British Antarctic Survey field report; Sotheby's Old Master Prints auction catalog; Kew Gardens specimen card.

### 7. Vernacular / found / un-designed
Street signage, amateur production, hand-made commercial work, or genuinely un-designed visual material. Often photographed in situ.
Examples: Greg Girard's Kowloon street-sign photography; Robert Venturi's *Learning From Las Vegas* photographs; hand-painted Japanese izakaya enamel sign; school-cafeteria menu board.

### 8. Natural form
A landscape, biological specimen, mineral, weather pattern, or other natural-world referent presented as a visual / structural model.
Examples: Hilma af Klint *Paintings for the Temple* notebook diagram; Hiroshi Sugimoto "Black Sea" seascape (1991); NOAA cloud atlas plate; Audubon *Birds of America* field plate; USGS bathymetric chart.

### 9. Craft / regional tradition
A craft artifact from a named place or named tradition — *not* the Designer's discipline (sampled separately at Step 5). Folk craft, vernacular trade, regional production.
Examples: Mashiko kiln-firing log strip; Korean Sulki & Min biennale catalog; Watain LP gatefold; Kyoto kakocho temple ledger; Mexican Day of the Dead calavera print run.

### 10. Media artifact
A film still, album cover, magazine spread, book cover, or media-production artifact.
Examples: Kyle Cooper Se7en title-sequence tape still; Stanley Kubrick *2001* monitor-wall production photograph; ECM Records sleeve by Barbara Wojirsch; Penguin Great Ideas cover by David Pearson.

## Generation procedure

Generate **exactly four candidates per category, 40 total**, conditioned on the chosen framing (Step 4) and the chosen designer (Step 5). Each entry is the artifact name plus minimal descriptor (≤10 words total), tagged with its category. Prefer concretely citable artifacts — exact named works over named bodies of work over general references.

Write the 40 seeds to `sampling.md` under `## Seeds`:

```
N. [category-name] artifact-name — brief descriptor (≤10 words)
```

The four candidates per category must be **distinct enough that they couldn't substitute for each other**. The 40 candidates must be **specific named artifacts**, not categories or styles — "a film still" fails; "the final frame of *Stalker* (1979) where Stalker reads to his daughter" passes. Vague candidates produce vague borrowings.

## Brief-fitness gate

Each of the 40 candidates passes the **borrowing-productivity test**:

> *"Could a Designer studying this artifact identify a specific visual move — a typography decision, a layout pattern, a color move, a composition choice, a treatment — that they could borrow into the build and have the result improve?"*

A "concrete borrowing exists" gate, not a "feels related to the framing" gate. Artifacts loosely resembling the framing but offering no specific visual move fail. Artifacts offering a clear borrowing direction — even if their overall register is far from the framing — pass.

**PASS examples** (framing = "1987 FT pink-paper art director"):
- `[historical artifact] FT Lex column print spread, 1987` — typography hierarchy + gutter rule + tabular numeric treatment
- `[interface / instrument] Bloomberg Terminal Level-2 book pre-2016` — tabular density, monospace numerics, cell-density logic

**FAIL examples** (same framing):
- `[natural form] Hilma af Klint *Paintings for the Temple* diagram` — no concrete typographic / compositional move for this brief
- `[contemporary practitioner] a 2024 Instagram post` — vague candidate, no specific borrowable move

For each FAIL: generate a replacement **from the same category** that satisfies the gate. Cap at **3 replacement iterations**. If a category still has no PASSing seed after 3 rounds, keep the best available and flag in the audit trail.

Record rounds in `sampling.md` under `## Seed fitness rounds`:

```
Round 1:
  1. [historical artifact] "1987 FT Lex column print spread" → PASS
  ...
  7. [natural form] "Hilma af Klint *Paintings for the Temple* notebook" → FAIL (no concrete typographic move; mismatch with framing's register)
  Replacement 7a: [natural form] "NOAA bathymetric chart 12300 series" → PASS (contour-line typography, legend convention transfers to data overlay)
  ...
```

Once 40 PASSing seeds (four per category) are established, sampling proceeds.

## Sample 2 uniformly

ms-sample 2 without replacement from the 40 PASSing seeds via the external gate (see `sampling-protocol.md` §The external sampling gate):

```bash
python3 -c "import random,time,sys; n,k=int(sys.argv[1]),int(sys.argv[2]); s=int(time.time()*1000); print(f'SEED={s}'); print(f'PICKS={sorted(random.Random(s).sample(range(n),k))}')" 40 2
```

Both chosen seeds enter the inspiration bank. The two need not be from the same category (in fact they likely won't be — the cross-category pair is the productive tension: a "historical artifact" seed + a "physical object" seed forces the Designer to find the visual move that bridges them).

## Present + confirm

Present the full 40-entry pool (with category tags), Bash command + stdout, the two chosen seeds, and a one-paragraph justification per seed: what specific visual move it offers, how the Designer will use it.

`new options`: discard the 40-pool and re-enumerate fresh. Other actions standard per `sampling-protocol.md` §The present + confirm pattern.

## Status-write

After locking the two seeds, `Edit` `pipeline_status.md` row 6 → `done`, with `Artifact` = `sampling.md §Seeds locked`. Update `Last updated`.
