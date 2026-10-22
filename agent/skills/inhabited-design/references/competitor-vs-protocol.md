# Competitor VS protocol

Step 8 of the pipeline samples two **direct competitors** — products users would actively compare the build against before deciding. They are the market context inside which the product will be received. A user evaluating a SOC analyst dashboard mentally benchmarks against Splunk and Datadog before forming an opinion. A user shopping Mashiko ceramics carries impressions from Heath Ceramics and MUJI into every product-page interaction.

Competitors are NOT anti-references. They are studied carefully, with the Designer building an explicit converge / diverge judgment for each design element: some elements are table-stakes for the domain (users already expect them; diverging without cause creates friction); others are deliberate differentiation points (where the brand identity, framing, and brief positioning demand a different move). The judgment is element-by-element, not a global sentiment.

Both sampled competitors enter the 7-anchor inspiration bank alongside the framing seeds (Step 6), the designer signature work (Step 5), and the domain-research references (Step 9).

## Brief-conditioned, not framing-conditioned

Competitors are determined by the brief's product category, domain, and target user — NOT by the sampled framing. A Mashiko ceramics e-commerce site with a "petrichor sensory" framing still has Heath Ceramics and MUJI as its competitors. Changing the framing to "West African indigo resist-dyeing logic" does not change the competitor pool; it changes the Designer's angle of approach into the same market.

## The 10 positioning categories

One candidate per positioning category, two candidates per category = 20-pool. Categories are positioning axes, not domain-specific labels — they apply across any brief.

### 1. Canon incumbent
The obvious category leader — the name the model would reach for first, the one users name when asked "what do you use?"
Examples: Red Bull (energy drinks); Heath Ceramics (US ceramics); Splunk (enterprise SIEM); Six Senses (luxury hospitality); Adobe (creative software).

### 2. Disruptor / oppositional
A product built explicitly on rejecting the canon's aesthetic and positioning — defined by what it refuses.
Examples: Liquid Death (refuses energy-drink-bro visual language); Cards Against Humanity (refuses Hasbro-corporate game design); Wacaco (refuses kitchen-appliance espresso ethos).

### 3. Premium / scarcity-positioned
Positions on price, access, or exclusivity rather than effect or differentiation. Limited availability, waitlists, members-only.
Examples: Aman Resorts; AmEx Centurion; Hermès; Macallan single-malt; Le Labo.

### 4. Functional / clinical
Positions on quantified results, transparency, evidence. Spec-forward presentation, mg-and-mL detail, study citations, ingredient panels as hero.
Examples: Magic Mind (energy + nootropics, dose-as-content); Athletic Greens / AG1; Examine.com; Glossier Future Dew.

### 5. Lifestyle / aspirational
Positions on identity, community, belonging — what owning this says about you. Lifestyle photography hero, named ambassadors, scene-coded copy.
Examples: Patagonia (climber identity); SoulCycle; Outdoor Voices; Cha Cha Matcha.

### 6. Legacy / unmodified traditional
A product that has not joined the modern brand-refresh cycle. Pre-rebrand. Often family-owned, often regional. Hasn't updated packaging or website in 10+ years — and that *is* the position.
Examples: Bawls Guarana; Quaker (original packaging); classic Coca-Cola; Wedgwood (original); Roget's Thesaurus print editions.

### 7. Adjacent-category encroacher
A product from a neighboring market encroaching on the brief's domain. Brings the conventions of *its* category into yours.
Examples (energy drink): sparkling water brands adding caffeine. (Cybersecurity): observability tools (Datadog) encroaching on SIEM. (Ceramics): kitchen-appliance brands releasing limited-edition tableware.

### 8. Indie / DIY / long-tail
A small, obscure, often single-person operation that genuinely competes for the same user attention but is not well-known. Regionally famous or scene-famous, but not household-name. "Small but talked about on design Twitter" is still canon — reach further.
Examples: a Bandcamp-only label release page; a one-person ceramics studio in Mashiko; an indie SIEM tool used by 200 SOC teams; a single-property hotel in rural Italy.

### 9. International / non-Western
A direct competitor from a geographic / cultural distance from the brief's primary market. Brings conventions from a non-Western market.
Examples (energy drink): Yakult; Sting Energy (India/SEA); Yokocha. (Cybersecurity): Trend Micro (Japan); Kaspersky (Russia); 360 Total Security (China). (Hospitality): Kachi Lodge (Bolivia); Aranya (Bangladesh).

### 10. Aesthetic anti-pole
A competitor whose design language is so different from the brief that studying it for *contrast* is the value, not direct comparison. Often from a different industry mapping obliquely onto the brief.
Examples (energy drink): a tombstone-style luxury watch ad. (Cybersecurity): a Japanese train timetable. (Ceramics): a McMaster-Carr industrial-parts catalog.

## Generation procedure

Generate **exactly two candidates per category, 20 total**. Each entry is the product name + minimal descriptor (≤6 words), tagged with its category.

Write the 20 competitors to `sampling.md` under `## Competitors`:

```
N. [category-name] competitor-name — brief descriptor
```

Categories 8 (indie/DIY), 9 (international/non-Western), and 10 (aesthetic anti-pole) exist to force the model out of canon. If these cells default to Western mid-tier alternatives, the enumeration has failed — actively reach for regional players dominant in non-US/EU markets, vertical-specific tools outside standard "best of" listicles, and non-English-language incumbents.

## Brief-fitness gate

Each of the 20 candidates passes the **direct-competition test**:

> *"Would a user shopping for this brief's product type actively compare this competitor to the build before deciding? Would studying its conventions inform a real design decision — either to borrow or to diverge?"*

A "lives in the same decision-space as the build" gate, not a "well-known brand in a remotely related market" gate. Walmart sells energy drinks but is not a competitor — it is the channel. Slack sells to enterprise customers but is not a competitor for a SOC dashboard — it is an adjacent tool.

**PASS examples** (energy-drink brief):
- `[canon incumbent] Red Bull` — direct comparison, conventions matter
- `[international / non-Western] Yokocha matcha energy` — functional-beverage competitor with non-US conventions

**FAIL examples** (same brief):
- `Walmart` — channel, not competitor
- `Coca-Cola Classic` (as canon-incumbent for energy) — categorical miscoding; Coke is the cola incumbent, not the energy incumbent

For each FAIL: generate a replacement **from the same category**. Cap at **3 replacement iterations**. If a category still has no PASSing competitor after 3 rounds, keep the best available and flag in the audit trail.

Record rounds in `sampling.md` under `## Competitor fitness rounds`:

```
Round 1:
  1. [canon incumbent] "Red Bull" → PASS
  2. [canon incumbent] "Monster Energy" → PASS
  ...
  4. [disruptor] "Walmart" → FAIL (channel, not a positioning-based competitor)
  Replacement 4a: [disruptor] "Yerba Mate Guayaki" → PASS (built on rejecting bro-energy conventions)
  ...
```

Once 20 PASSing competitors (two per category) are established, sampling proceeds.

## Sample 2 uniformly

ms-sample 2 without replacement from the 20 PASSing competitors via the external gate (see `sampling-protocol.md` §The external sampling gate):

```bash
python3 -c "import random,time,sys; n,k=int(sys.argv[1]),int(sys.argv[2]); s=int(time.time()*1000); print(f'SEED={s}'); print(f'PICKS={sorted(random.Random(s).sample(range(n),k))}')" 20 2
```

Both chosen competitors enter the inspiration bank. They need not be in the same tier — a sample of one dominant player + one long-tail regional tool is valid and often generative (the contrast in design conventions between them is instructive).

## Present + confirm

Present the full 20-entry pool, Bash command + stdout, the two chosen competitors, and a one-paragraph justification per competitor: what conventions it carries, what expectations it sets in users, why studying it (to borrow or diverge) is productive.

`new options`: discard the 20-pool and re-enumerate fresh. Other actions standard per `sampling-protocol.md` §The present + confirm pattern.

## How the Designer treats the 2 sampled competitors

The two competitors enter the inspiration bank as **references**, not anti-references. For each, the Designer builds an explicit **converge / diverge judgment table** with one row per design element and three columns:

- **`verdict`**: `borrow` or `diverge`. No other values. `borrow` means table-stakes for the domain — users expect it; diverging creates friction. `diverge` means deliberate differentiation — the brief positioning, framing, or brand identity requires a different move.
- **`rationale`**: one line explaining why the verdict serves the brief or framing. Not "looks nice" — a specific claim about user expectation, domain convention, brand positioning, or framing logic.
- **`build location`**: CSS selector, region, or component where a `borrow` surfaces. For `diverge`, write `N/A`.

Design elements to cover (minimum; extend per brief):

| Category | Examples |
|---|---|
| Navigation | top nav, left rail, bottom bar, command palette, breadcrumbs |
| Hero / landing | hero layout, headline treatment, primary CTA placement |
| Typography | typeface family, size scale, weight usage, line height |
| Color | primary palette, accent, surface colors, semantic colors |
| Layout | grid system, column count, density, white-space logic |
| Motion | transition style, animation timing, microinteraction patterns |
| CTAs | primary button shape, label convention, placement |
| Empty / error states | copy, illustration approach, inline validation, toast/alert |
| Data display | table conventions, chart types, density, labeling |
| Search | placement, results presentation, filter UI |

Every element in the build must have a verdict row. No `unclear` / `tbd` / blank entries. If an element is not in the build at all, omit the row.

The judgment table lives in `borrowings_v{cycle}.md`. The adversarial critic scores `fits competitor judgment` based on it and penalizes two failure modes:

1. **Silent convergence** — the build matches a competitor's pattern without a recorded `borrow` verdict.
2. **Arbitrary divergence** — a `diverge` verdict with empty, generic, or framing-inconsistent rationale.

Both cap the rubric score regardless of how the build looks in isolation.

## Worked example

Brief: SOC analyst dashboard. Sampled competitors: **Splunk** (idx 0) and **Datadog** (idx 2).

Fragment of the converge / diverge judgment table:

```
Element            | vs Splunk                                                         | vs Datadog
-------------------|-------------------------------------------------------------------|-------------------------------------------------------------------
Severity color     | borrow (red=critical, amber=warn — domain convention; analysts    | borrow (same — consistent convention across both incumbents)
                   | trained on this; diverging causes triage delay)                   |
                   | build: .severity-badge, .alert-row[data-level]                    | build: same
Left navigation    | diverge (no left rail — command-palette only; left rail trains    | diverge (same rationale — command-palette is the differentiation)
                   | analysts to browse; command palette trains them to query)         |
                   | N/A                                                                | N/A
Empty state        | diverge (no "Nothing to show" placeholder — show last-resolved    | borrow (timeline-with-zero-events from Datadog is correct: shows
                   | incident as context; empty-queue should feel earned, not absent)  | time passage, not absence; matches our timeline structure)
                   | N/A                                                                | build: .timeline-container[data-events="0"]
Time picker        | borrow (relative + absolute toggle is the domain standard)        | borrow (same — analysts think in relative time except during
                   | build: .time-picker, [data-mode="relative"], [data-mode="abs"]    | post-incident review; both modes must be present)
                   |                                                                    | build: same
Incident timeline  | diverge (no horizontal scrubber — fold severity rail into         | diverge (same — Datadog's scrubber-plus-chart is two elements
                   | timeline; vertical spatial logic matches the framing's            | doing one job; collapse into severity-coded vertical rail)
                   | tide-table temporal structure)                                    |
                   | N/A                                                                | N/A
Alert density      | borrow (high-density rows; 20+ alerts visible without scroll)     | borrow (same — Datadog's default density is also high)
                   | build: .alert-table tr, line-height values in design tokens       | build: same
```

Every element in the build has an entry per competitor. The table is produced before design code is written and attached to `borrowings_v1.md`. The Critic reads it during review and verifies the build reflects the verdicts.

## Status-write

After locking the two competitors AND attaching the judgment tables to `borrowings_v1.md`, `Edit` `pipeline_status.md` row 8 → `done`, with `Artifact` = `sampling.md §Competitors locked + borrowings_v1.md §Competitor judgment tables`. Update `Last updated`.
