# Borrowing summary protocol

The discipline that converts "borrowing X from this" lines into **per-iteration pixel-traceable evidence** of each visual element transferred from each reference and each competitor to the build. In the inhabited-design skill this protocol has two parts: the **per-reference borrowing log** (inherited from the parent skill) and the **per-competitor converge/diverge table** (new in this skill, required by `competitor-vs-protocol.md` and scored by the critic via `adversarial-critic-protocol.md` §fits competitor judgment).

---

## When to write it

For each iteration of the build:

- **Critic loop (v1, v2 …):** write `borrowings_v{cycle}.md` in `.inhabited/`. One file per critic cycle; update in-place if the cycle restarts on the same build.
- **ICP loop:** write `borrowings_iter_{N}.md` per iteration (where N is the ICP iteration index).

Both files must be complete before the Designer returns "build done." The critic reads the borrowings file in full before scoring any rubric factor.

---

## Per-reference borrowing log

For every reference in the inspiration bank, the Designer logs in `borrowings_v{cycle}.md`:

**(a) The named, specific visual element borrowed** — typeface, hex color, glyph, layout pattern, composition move — NOT a principle like "honest density."

**(b) The selector / region in the build where it surfaces.**

**(c) The reference screenshot citation** (file path or URL of the reference image used as evidence).

### What counts as a named visual element

- **Typeface:** a specific font face by name (e.g., "Mr Eaves Modern at 96px caps")
- **Color:** a specific hex value or named color (e.g., "#C8412B Émigré 1 red")
- **Color scheme / palette:** a multi-color palette borrowed from a reference as a HARD GATE — minimum 3 colors beyond pure neutrals (white/black/grey don't count), each with hex, role in reference, and role in build
- **Glyph:** a specific character or symbol (e.g., "the Émigré asterisk," "the MUJI 無印良品 vertical kanji")
- **Layout pattern:** a specific compositional move (e.g., "Florent menu's flush-left dish + dotted-leader + flush-right price")
- **Proportion:** a specific size/scale relationship (e.g., "the 1:7 wordmark-to-page-width ratio from Émigré 1")
- **Composition:** a specific structural move (e.g., "the horizon line bisecting the field at 56% height from MUJI Uyuni")
- **Image treatment:** a specific visual transformation (e.g., "halftone grain texture overlay from a Polish poster")

### What does NOT count

- **Principles:** "type-as-object honesty," "less but better," "considered restraint," "honest density." Abstractions that can apply to anything; they let the model claim borrowing without transferring a visible artifact.
- **Voices:** "vernacular," "literate," "anti-bro." Voice goes in copy, not in the visual borrowing log.
- **Affordances:** functional borrowings go in a separate section if needed; they don't count for the visual rubric.
- **Negations:** cautionary references don't belong in the inspiration bank. Move them to `claude_anti_defaults.md`.

### File format — per-reference section

```markdown
# Borrowings — {{cycle / iteration label}}

## Palette borrowed from: {{reference name + file path}}

**Full palette (≥3 colors beyond pure neutrals):**
| Hex | Role in reference | Role in build | Selector |
|---|---|---|---|
| #C8412B | Mr Eaves specimen field | section background | `.section.featured` |
| #F5EBD0 | Mr Eaves specimen type-on-red | type on featured section | `.section.featured h2` |
| #E8C547 | Mr Eaves asterisk yellow | yohaku asterisk | `.day.empty .asterisk` |
| #A8741A | Mr Eaves caption ochre | active day stripe | `.day.active::before` |

**Distinct hues used (saturation > 10%):** {{count}}.
**Distinct hues in the source reference:** {{count}}.
**Lean direction:** more / same / less color than the reference.

---

## Reference 01: {{Source name + file path}}

**Visual elements I borrowed (named, specific):**
1. {{Element 1 — e.g., "the red field at #C8412B"}} → applied at {{selector / region}} → visible at {{build screenshot path}}
2. {{Element 2 — e.g., "the cream-on-red stacked cap headline"}} → NOT applied / DROPPED (reason: {{...}})

**Reference image evidence:** the named elements I'm claiming come from {{reference file path}} — specifically, in that image I can point at: {{description of what's in the reference}}.

**Build pixel evidence:** the borrowed elements appear in {{build screenshot file path}} — specifically: {{description of where in the build}}.

---

## Reference 02: ...
```

Every reference in the bank gets an entry — including cautionary references, which will have all elements marked DROPPED and which should be migrated out of the inspiration bank under the current methodology.

---

## Per-competitor converge/diverge table

For **each of the 2 sampled competitors** (from `competitor-vs-protocol.md`), the borrowings file includes a complete converge/diverge judgment table. This table is produced **before design code is written** and is the audit trail that lets the critic verify deliberate convergence/divergence.

### Table structure

Each row covers one design element. Required columns:

| Column | Content |
|---|---|
| **element** | design element category: nav, hero, type, color, layout, motion, CTAs, empty states, error states, settings, data display, onboarding, icons, search |
| **verdict** | `borrow` or `diverge` — no other values. `borrow` = table-stakes domain convention; users expect it, diverging creates friction. `diverge` = deliberate differentiation; the brief, framing, or brand positioning requires a different move. |
| **rationale** | 1 line: why this verdict serves the brief or framing. Must be specific — tied to user expectation, domain convention, brand positioning, or the framing's logic. |
| **build location** | selector or region where the verdict surfaces. `N/A` for `diverge` verdicts — the absence is intentional. |

### Rules

- Every element that appears in the build must have a verdict row. No `unclear`, `tbd`, blank rows, or deferred entries.
- If an element is not present in the build at all, omit the row rather than marking the verdict column `N/A`.
- Both competitors have their own table. Neither may be left incomplete while the other is present.
- The tables live in `borrowings_v{cycle}.md` alongside the per-reference sections.

### Worked example — SOC dashboard (Splunk + Datadog as sampled competitors)

Brief: SOC analyst dashboard — real-time threat detection, alert triage, and incident response for enterprise security teams.

**Competitor A: Splunk** (dominant player)

| element | verdict | rationale | build location |
|---|---|---|---|
| severity color | borrow | red=critical, amber=warn is domain-trained convention; analysts carry this mapping from all prior tooling; diverging causes triage delay | `.severity-badge`, `.alert-row[data-level]` |
| left navigation | diverge | command-palette-only navigation; left rail trains analysts to browse, command palette trains them to query — matches the brief's query-first UX goal | N/A |
| default font | diverge | framing calls for a different typographic register than Splunk's utilitarian mono; typeface choice is driven by framing, not incumbency | N/A |
| empty state | diverge | instead of "Nothing to show" placeholder, show last-resolved incident as context; empty-queue should feel earned, not absent | N/A |
| time picker | borrow | relative + absolute toggle is domain standard; removing it creates expert friction for analysts who think in relative time except during post-incident review | `.time-picker`, `[data-mode="relative"]`, `[data-mode="abs"]` |
| alert density | borrow | high-density table rows expected; analysts need 20+ alerts visible without scroll; Splunk defaults to this; sparse layouts mismatch the domain's workload | `.alert-table tr`, line-height design tokens |

**Competitor B: Datadog** (dominant player)

| element | verdict | rationale | build location |
|---|---|---|---|
| severity color | borrow | same convention as Splunk — consistent across both incumbents; users carry this expectation regardless of which tool they came from | `.severity-badge`, `.alert-row[data-level]` |
| left navigation | diverge | same rationale as Splunk diverge — command-palette navigation is the differentiation point | N/A |
| default font | diverge | Datadog uses Inter; our typeface is framing-driven, not convention-driven | N/A |
| empty state | borrow | timeline-with-zero-events pattern from Datadog is correct: it shows time passage, not absence; matches our timeline structure | `.timeline-container[data-events="0"]` |
| time picker | borrow | analysts think in relative time except during post-incident review; both modes must be present; domain has converged on this | `.time-picker`, `[data-mode="relative"]`, `[data-mode="abs"]` |
| alert density | borrow | Datadog's default density is also high; sparse layouts mismatch the domain's workload | `.alert-table tr`, line-height design tokens |

Note that where both competitors agree (severity color, time picker, alert density), the Designer records the same `borrow` verdict for both — these are table-stakes domain conventions. Where the Designer diverges from both (left nav, font), the same rationale applies to both tables, but each table still gets its own row with an explicit verdict.

---

## Lazy-judgment failure modes

The adversarial critic will flag the following lazy-judgment patterns in the converge/diverge tables:

### Silent default

A nav, layout, or UI pattern copies the competitor's exactly, but no `borrow` row exists in the table. The build matches the competitor but the decision wasn't made — it just happened. This is the primary failure mode the table exists to prevent: design-by-inertia disguised as design-by-intention.

The critic will pixel-compare the build against the competitor and flag any close visual match that lacks a corresponding `borrow` entry. Every match must be recorded as a deliberate choice.

### Silent divergence

Something in the build looks nothing like the competitor — different layout, different interaction model, different visual grammar — but no `diverge` row exists for it and no rationale was given. The build differs from the competitor but no reason was recorded. This is a structural omission: the difference exists, but it wasn't a decision.

The critic will identify any element present in the build that departs structurally from the competitor without a logged `diverge` verdict.

### Hollow rationale

Rationale cells that contain placeholder justifications without specific claims:

**Unacceptable:** "diverge because differentiation," "borrow for branding consistency," "diverge — fresh take," "borrow — modern feel," "diverge because we want to be different," "borrow to align with the space."

**Acceptable:** "diverge because the framing 'monastic abstinence' rejects high-contrast urgency CTAs, which Datadog defaults to in every alert row," "borrow because severity-color convention is domain-trained and two years of analyst habit; breaking it extends triage time," "diverge because the brief explicitly positions this tool as query-first, which is structurally incompatible with left-rail browse navigation."

The minimum bar for a rationale: it must name something true about the brief, the framing, the user, or the domain that would change if the verdict were reversed. If flipping the verdict wouldn't require updating the rationale, the rationale is hollow.

### Rationalizations after the fact

The table must be written before design code is produced. Post-hoc rationale — written to explain a build that already exists — is structurally unreliable: the Designer is explaining what happened rather than recording what was decided. The critic will look for timestamps or ordering evidence in the file to identify this. A table that was clearly written after the build to justify existing choices counts as hollow across all its rows, regardless of individual rationale quality.

"Borrowed by negation" claims — a divergence framed as a borrow, or vice versa — don't count. If the build departs from the competitor, the verdict must be `diverge`, even if the Designer would prefer to frame it as "borrowing the inverse." The table must be honest about what the build does, not what the Designer intended.

---

## Verification by critic

### Per-reference verification (from parent skill)

The critic, when scoring `fits sampled inputs`:

1. Read `borrowings_v{cycle}.md`
2. For each reference entry, verify:
   - At least one named, specific visual element is claimed (not a principle)
   - The named element is actually present in the reference image (Read the reference file)
   - The named element is actually present in the build (Read the cited build screenshot)
3. Cite both files in the verdict for each borrowing
4. Drop the score by 1 per rationalization, by 1 per missing element, by 2 per cautionary-only reference still in the bank

### Per-competitor verification (new in this skill)

The critic, when scoring `fits competitor judgment`:

1. Read both competitor tables in `borrowings_v{cycle}.md`
2. For each `borrow` verdict:
   - Pixel-compare the reference competitor image to the build screenshot at the recorded build location
   - Confirm the borrowed element is structurally present and visually recognizable
   - A `borrow` verdict that cannot be verified at the recorded selector drops the score by 1
3. For each `diverge` verdict:
   - Verify a structural difference exists between the build and the competitor at that design element
   - The absence must be genuine — not a diluted or partial presence
   - A `diverge` verdict where the element appears in attenuated form (e.g., "no left nav" but a collapsible side panel is present) counts as a silent default, not a divergence
4. For hollow rationales:
   - Apply the minimum-bar test: would flipping the verdict require updating the rationale? If not, the rationale is hollow
   - Drop the score by 1 per hollow rationale row
5. For silent defaults and silent divergences:
   - Pixel-compare the build against each competitor screenshot
   - Any close visual match without a `borrow` entry is a silent default — drop the score by 2
   - Any structural departure without a `diverge` entry is a silent divergence — drop the score by 1

Rationalizations do not count as evidence. Each row in the competitor tables requires concrete build evidence (a screenshot + selector confirmation) for `borrow` verdicts, and a concrete structural diff (a screenshot + absence confirmation) for `diverge` verdicts. The critic's job is verification, not interpretation.

A build with complete, honest, pre-code competitor tables and verifiable verdicts can earn 10/10 on `fits competitor judgment`. A build with silent defaults, hollow rationales, or post-hoc tables cannot earn above 6/10 regardless of how well it looks in isolation.

---

## Attribute-binding manifest (NEW in v5)

The per-axis output decomposition (`axis-decomposition-protocol.md`) requires that every output element name the specific sampled axes it derived from. This produces the **attribute-binding manifest**, appended to `borrowings_v{cycle}.md` after the per-reference and per-competitor sections.

### Why this exists

The v5 axis-decomposition protocol restricts the context per sub-pass — when generating `imagery`, the Designer subagent only sees framing + seeds + designer + constraint, not typography or competitors. The attribute-binding manifest is the **paper trail** that proves the restricted-context discipline was honored: each output element traces explicitly to the inputs that should have produced it.

T2I attribute-binding papers (Attend-and-Excite, T2I-CompBench) showed that explicit attribute-binding annotations improve compositional fidelity because they force the model to commit to a specific axis-output mapping rather than averaging. v5 imports this into the inhabited-design output protocol.

The critic uses the manifest to score factor 4 (`fits axis manifestation` in `adversarial-critic-protocol.md`): does each output element actually reflect the specific sampled axes it claims to derive from?

### File format — attribute-binding manifest section

Append to `borrowings_v{cycle}.md` after the per-competitor tables:

```markdown
## Attribute-binding manifest

### style_tags
- style_tags[0] = "tropical-modernist"
  derived from: framing "Bawa Sri Lankan tropical-modernist architect" — category descriptor
- style_tags[1] = "photo-monograph"
  derived from: framing's photographic-monograph register

### color_palette
- color_palette[0] = "#1A1F22 long-exposure shadow"
  derived from: framing "Sugimoto stillness" + seed "Sugimoto Seascapes monograph plate"
- color_palette[1] = "#3A4541 fog-saturated cypress"
  derived from: seed "Cloud-forest atmosphere" + constraint "no near-black UI chrome"
- color_palette[2] = "#A8A293 silver-gelatin paper"
  derived from: seed "Steichen Family of Man catalog plate-paper warmth"
...

### imagery
- imagery[0] = "long-exposure cloud-forest plates, no people"
  derived from: framing "Sugimoto large-format long-exposure stillness"
              + seed "Sugimoto Seascapes monograph plate"
              + constraint "no cabin/interior photography on first paint"
- imagery[1] = "horizon-line anchored composition across all panels"
  derived from: framing's photographic-monograph compositional logic
              + seed "Steichen Family of Man wide-frame editorial"

### surface_treatment
- surface_treatment[0] = "scanned silver-gelatin paper substrate"
  derived from: framing "long-exposure monograph register"
              + designer "Veronika Burian editorial-paper sensitivity"
- surface_treatment[1] = "no gradients — flat tonal fields only"
  derived from: constraint "no near-black UI chrome" + framing's photographic register

### ornament
- ornament[0] = "plate edition number above each photograph"
  derived from: framing "monograph plate convention"
              + designer "Burian's tabular figure discipline"

### motion
- motion[0] = "no transitions over 80ms — printed-monograph register"
  derived from: framing "long-exposure stillness" + constraint "page-as-printed-object discipline"

### mood
- mood[0] = "atmospheric"
  derived from: framing's emotional register (Sugimoto stillness)
- mood[1] = "patient"
  derived from: framing's long-exposure temporal register

### style_tags / inspirations / key_visual_elements
(per the same per-element derivation format)
```

### Rules for the manifest

1. **Every output element must have an entry.** No element may be unbacked. If an output element can't be traced to specific sampled inputs, it shouldn't be in the output.

2. **Each entry names specific inputs, not abstractions.** "derived from: framing's mood" is too vague. "derived from: framing 'Sugimoto long-exposure stillness' + constraint 'no cabin/interior on first paint'" is specific.

3. **Cross-axis derivation is fine.** An imagery element can derive from framing + seeds + constraint (multiple input axes). But it cannot derive from inputs the sub-pass wasn't supposed to see (e.g., the imagery axis sub-pass doesn't see competitors, so imagery elements cannot claim to derive from competitors).

4. **One-to-many is fine.** A single input axis can produce multiple output elements. (Framing typically conditions most output fields.)

5. **Many-to-one is fine.** A single output element can cite multiple input axes as joint derivation.

6. **The manifest is generated alongside each sub-pass.** Not retro-fitted at the end. Each output element gets its manifest entry as it's produced.

### Lazy-manifest failure modes

- **"All from framing"** — every output element trivially derived from the framing. The Designer didn't use the other sampled inputs. The critic catches this by counting per-axis input citations: if framing is cited in >70% of manifest entries, the score drops.
- **"Generic derivation rationale"** — entries that say "derived from: framing's general direction" without naming a specific aspect. Drops the score by 1 per generic entry.
- **"Phantom derivation"** — claims derivation from an input the sub-pass wasn't supposed to see (e.g., color_palette element claiming to derive from competitors). The critic catches via context-rule check; auto-fails the manifest, requires regen.

### Critic verification

The critic, when scoring `fits axis manifestation` (factor 4 in the 4-factor rubric — see `adversarial-critic-protocol.md`):

1. Read the attribute-binding manifest in `borrowings_v{cycle}.md`
2. For each output element claim:
   - Verify the claimed sampled inputs exist in `sampling.md`
   - Verify the claimed inputs were in the sub-pass's restricted context for that axis (per `axis-decomposition-protocol.md`)
   - For visually verifiable claims (colors, type, imagery), pixel-compare the build to the cited sampled inputs
3. For axes lacking output elements: drop the score by 2 per missing axis
4. For unbacked output elements: drop the score by 1 per element
5. For phantom derivations: drop the score by 2 per phantom entry
6. For >70% framing-only derivations: drop the score by 2 (cross-axis bleeding into framing-dominance)
