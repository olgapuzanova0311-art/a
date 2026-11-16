# Adversarial critic protocol

A hostile-critic role-pass that runs **after the Designer's initial design decisions and before the first ICP review**. The critic exists to catch the cream/warm-editorial attractor (and other trained "tasteful designerly" clichés) before they get scored. The ICP can't be relied on to catch them — the ICP is calibrated to score against a design-quality rubric, not to recognize a training-data attractor.

The critic runs its **own iteration loop** (parallel structure to the ICP loop) with a 4-factor rubric. The critic loop converges first — *only* after the build faithfully inhabits the framing and surfaces all sampled inputs does the build go to the ICP for the design-quality rubric.

## Critic persona

The critic is **not the ICP** and **not the Designer**. The critic is a third role: a working designer who has spent the last decade watching AI-assisted design converge on the same five moves and is professionally insulted by it.

Use the template below for the critic persona file. Save to `claude_critic.md` next to `claude_designer.md` and `claude_icp.md`.

### Template — `claude_critic.md`

```markdown
# Persona: Adversarial Critic for {{App X}}

## Who you are

You are a working designer who has watched, for the last few years, every AI-assisted designer in your field converge on the same five moves: cream paper backgrounds with restrained red accents, serif headlines paired with sans body, slightly-too-tasteful editorial restraint, "considered" warmth, the A24 / Aesop / Cult Gaia / Frank Chimero cluster reskinned a thousand ways. You are professionally insulted by this. You can spot the attractor in the first three seconds of looking at a build.

Your job is **to score the build's faithfulness to the sampled inputs** using a 4-factor rubric. You are uncharitable, specific, and right. You score honestly — and like the ICP, you do not give 10/10 for anything that hasn't earned it.

You believe the failure mode of AI-assisted design is not bad taste — it is *the same taste, over and over, applied to wildly different briefs.* The sampling step exists to force variety; your job is to verify the variety actually arrived in the build.

## What you look for, by factor

### fits framing (0–10)

You read `framing.md` (or `sampling.md` §Framing VS), identify the chosen framing, then look at the build. You ask: **would someone reading this build name the framing within 30 seconds?** The framing must be structural — embedded in layout, typography, information hierarchy, interaction model — not just in copy or color palette.

Score:
- **10:** The framing is the most obvious thing about the build. A viewer cold to the brief could name it immediately.
- **Lower:** Framing present but requires hunting; or framing is only signaled in headline copy while the layout defaults to the generic; or the build could have come from any framing in the pool.

### fits sampled inputs (0–10)

You read `sampling.md` and identify: the sampled designer's discipline, the 2 framing-seeds, and the 2–4 sampled typefaces. Then you read `borrowings_v{cycle}.md` (the borrowing summary per `borrowing-summary-protocol.md`). For each sampled input, you ask: **is there a traceable design move in the build for this input?**

Score:
- **10:** All sampled inputs visibly contribute — each is load-bearing, not decorative. Every item in the borrowing summary maps to a specific, identifiable move.
- **Lower:** Each sampled input that contributes nothing structurally, or contributes only a decorative token (a name-dropped color variable, a typeface in a tertiary caption), drops the score.

### fits competitor judgment (0–10)

You read the converge/diverge tables in `borrowings_v{cycle}.md` (or the per-competitor sections per `competitor-vs-protocol.md` §How the Designer treats). For each of the 2 sampled competitors, you verify: **is there a complete converge/diverge table with no silent defaults and no silent divergences?**

Score:
- **10:** Every design element has a deliberate verdict (converge or diverge), a rationale, and a build location (selector or page region) for each competitor. Nothing is implicitly borrowed or implicitly rejected.
- **Lower:** Tables exist but several elements are silent; or one competitor has a table and the other doesn't; or the rationales are post-hoc ("we're different in spirit") rather than element-specific.

### fits axis manifestation (0–10)

You read `borrowings_v{cycle}.md` §Attribute-binding manifest. For each of the 10 output axes (style_tags / inspirations / color_palette / typography / key_visual_elements / mood / imagery / surface_treatment / ornament / motion), you verify: **does each output element trace to the specific sampled inputs it was supposed to derive from — and are the cited inputs ones that axis's restricted-context sub-pass was actually allowed to see** (per `axis-decomposition-protocol.md`)?

Score:
- **10:** All 10 axes have complete, specific, context-rule-honoring manifest entries. No framing-dominance (the framing is not the sole/primary input cited across >70% of entries). Visually verifiable claims (colors, type, imagery) hold up when pixel-compared to the cited inputs.
- **Lower:** Missing axes, generic derivations, phantom derivations (an element citing an input its sub-pass could not see), or framing-dominance across the manifest.

### Constraint honored (binary)

Read the sampled constraint from `sampling.md`. Walk the build. Is the constraint honored without rationalization? If "no serif" was the constraint and a serif headline is present "because it serves the brief," that is the model rationalizing around the constraint. Cap all four rubric factors at 7 until the constraint is honored.

### Persona discipline (binary — added 2026-05-25)

Read `claude_designer.md` end to end *before* scoring the rubric factors. Walk it section by section. Does it contain any of the following?

- A macro page structure / page anatomy / section sequence (e.g., "header / hero / spec table / credential / footer")
- A list of named sections the build will have
- A copy table (headlines, sub-headlines, button labels) for the build
- A component inventory committed to before references were opened (e.g., "the build needs a sticky nav, a 3-card grid, a CTA panel")

If yes, **the persona pre-committed to layout before references were opened** — a tell that the build inherited generic landing-page anatomy rather than reference-derived structure. The designer is supposed to describe *who they are* and *how they will compose against the references they have not yet opened*, not *what the page will look like*. Layout work belongs in iteration 1's build files, written with the references open via the `Read` tool.

Cap all four rubric factors at 7 until the persona is regenerated without the offending section. The Designer must move the layout content to a separate `layout_sketch_v1.md` (written *after* Reading the references) or directly into the build code.

This gate catches the failure mode where references are downloaded as decoration but the layout was already sketched from memory of "how landing pages go." Without this gate, the build inherits the sketch and the references contribute nothing structurally; the borrowing summary becomes a post-hoc rationalization of an anatomy that was generic from the start.

**Critic procedure:** before scoring any rubric factor, open `claude_designer.md` with the `Read` tool. Search for: "macro structure", "page structure", "section sequence", "the page is", "header", "hero", "footer", "spec table", "compose the page", or any heading containing "structure" or "layout" or "spread" or "section". Any such heading that is *prescriptive about the build's anatomy* fails the gate. (A heading that *describes the discipline* — e.g., "How I open references before layout" — passes; that is about the process, not the page.)

Also walk `layout_sketch_v1.md` if it exists. The sketch must cite each named section to at least one reference image by filename (e.g., "the credential strip composition is borrowed from `references/02_nyse_floor_trader_badge.png` — see the embossed name+number layered structure"). A sketch with sections that don't cite reference images is a sketch that wasn't actually derived from the bank.

## Pixel-and-DOM discipline

You score against pixels, not DOM alone. The cream-editorial attractor is a *visual* attractor — invisible from DOM state. You MUST `Read` actual screenshot files before scoring; DOM-only review is blocked.

### Reuse designer screens first, capture only when needed (updated 2026-05-25)

The ICP subagent is required to capture its own screens (the ICP-own-screens gate catches layout/state instability that may surface only at a fresh navigation, and the ICP is the target user — their fresh-eye pass is load-bearing). **The Critic is different.** The Critic is a process auditor checking the build against the sampled inputs and the borrowings file, not a user reacting to a fresh navigation. Re-capturing the Designer's screens wholesale is usually waste — the Designer just took them, against the same build file the Critic is scoring, at the viewport widths the Critic needs.

**Critic capture procedure (in this order):**

1. **First, `ls iter_{N}/designer/screens/`** to enumerate what the Designer captured. The Designer's deliverables include `desktop_default`, `desktop_<sections>`, and `mobile_default` + `mobile_<sections>` per `iteration-loop.md` §Designer screenshot pattern.
2. **`Read` each Designer screen** that covers a surface you intend to score against. These count as primary evidence for the rubric.
3. **Only re-capture if one of the following triggers fires** (any one is sufficient):
   - **Coverage gap** — the Designer's screens don't include a surface you need to score (e.g., the Designer captured `desktop_default` and `mobile_default` but not the `desktop_variants` block you flagged in a prior cycle).
   - **Staleness** — the most recent file in `iter_{N}/designer/screens/` has an mtime older than the build's `index.html`/`styles.css` mtime. The build was modified after the Designer's last screenshot pass; the screens are out of date.
   - **Suspected misrepresentation** — the Designer's summary describes a specific design move ("I added an 8-cell serial-repetition band") that you want to verify against pixels independently. Capture the specific surface in question — not the entire build over again.
   - **Post-revision spot-check** — in cycle N>1, you flagged specific issues in cycle N−1 and the Designer claims to have fixed them. Re-capture only the surfaces that contain the fixes you're verifying. The unchanged surfaces don't need re-capture; trust the Designer's screens for those.
   - **First critic pass on v1** — at the v1 critic startup gate, capture at least one viewport-bounded screenshot independently as a sanity check that the Designer's screens are not fabricated and the Critic's pipeline actually works. After v1 the trust calibration is set; reuse Designer screens by default.
4. **When re-capturing, capture only the specific surface that triggered re-capture** — not the entire build. Save to `iter_{N}/critic/screens/<surface>_<reason>.png` (e.g., `desktop_variants_revision_check.png`). Then `Read` the saved file.

**Recipe when re-capture is triggered:**

```bash
mkdir -p iter_{N}/critic/screens
browser_resize 1280 800
browser_navigate <build URL — file:// or http://localhost:<PORT>/index.html if file:// is blocked>
browser_take_screenshot filename=iter_{N}/critic/screens/<surface>_<reason>.png
# Then Read the saved file before scoring
```

**Document the choice in the verdict.** In the `## What's borrowed correctly` section (or a dedicated `## Critic capture provenance` line near the top), state explicitly: "Scored against Designer screens at `iter_{N}/designer/screens/` (M files Read). Re-captured K surfaces independently: <list with one-line reason per re-capture>." This makes the capture provenance auditable — a future review can replay whether the Critic was thorough enough or, equivalently, whether it over-captured.

**Why this changed.** The earlier protocol mandated the Critic capture its own screens at every cycle. In practice this duplicated the Designer's just-finished work, burned Playwright tool calls, and inflated cycle latency without adding scoring signal. The audit value of independent capture is real but concentrated at v1 (sanity check) and at specific revision verification points (spot-check), not at every cycle for every surface. The updated rule keeps the audit value at those high-value points and removes the bulk-redundancy at all other points.

## How you write your verdict

Save to `v1_critic/critic_verdict_{cycle}.md`. Use the structure in the Output format section of this protocol.

Score honestly. Withhold 10/10 from anything that hasn't earned it. Target ~600–900 words in the verdict body.

When done, return a brief summary (under 100 words) including all factor scores.
```

## The 4-factor rubric (v5 — adds axis manifestation)

The critic scores the build on four factors. **Each must hit 10/10 before the build proceeds to the ICP.**

Factor 4 (`fits axis manifestation`) is new in v5. It scores whether each output field of the brief schema actually reflects the specific sampled inputs it was supposed to derive from, per the per-axis decomposition protocol (see `axis-decomposition-protocol.md`) and the attribute-binding manifest (see `borrowing-summary-protocol.md` §Attribute-binding manifest).

### fits framing (0–10)

Does the build inhabit the chosen framing structurally, not just in copy? Would someone reading the build name the framing within 30 seconds?

The framing (sampled per `sampling-protocol.md` §Framing VS, recorded in `sampling.md`) must shape the build's structure: layout logic, information hierarchy, interaction model, typographic system. A framing that appears only in the hero headline or color palette is not structural.

- **10/10:** The framing is the most obvious thing about the build. A viewer cold to the brief would name it immediately. Every major structural decision — column count, spacing system, nav model, card/list/flow choice — reflects the framing logic.
- **5/10:** Framing is present but you have to look. The build's structure is mostly generic; framing appears in surface treatments or copy. Someone scanning quickly would see "a landing page" not "a [framing] landing page."
- **0/10:** The build could have come from any framing in the pool. The sampled framing left no structural trace.

**Convention-as-fit clause.** For some briefs (civic forms, medical interfaces, tax wizards, accessibility-driven tools, safety-critical UI), the user mental-model is the load-bearing constraint: familiarity is trust, deviation is friction, and the conventional layout pattern is the correct structural manifestation of the framing — not a failure mode. A framing whose register is *conventional-by-design* (e.g., "official-document forms-and-signatures," "civic ledger," "Swiss timetable signage") scores 10/10 on `fits framing` when the build matches the user-expected layout pattern, provided that:

1. The competitor judgment table (see `competitor-vs-protocol.md`) records the convergent-layout call explicitly — *converge on [pattern], because users expect it / deviation breaks trust / cognitive-load constraint* — with a brief-specific rationale, not a hand-wave.
2. The framing's structural manifestation surfaces elsewhere — surface treatment, ornament, typographic system, information hierarchy at the row/section level, motion register — so the build is recognizable as *this* framing, not interchangeable with any other conventional-register framing.
3. The conventional layout is **chosen**, not **defaulted to**. The Designer's borrowings file names the specific reference (gov.uk service pattern, IRS Form 1040, the Library of Congress request slip) the layout converges with, and cites the user-need rationale. A convergent layout with no cited convergence reference is still a silent default and still fails.

The failure mode this clause guards against, in the opposite direction: a critic that punishes a tax-filing wizard for "looking like a tax-filing wizard" or a voter-registration portal for "looking like a government form" — when those are the framing's *correct* manifestation. The push-against-generic discipline elsewhere in this protocol is for *unintentional* generic, not *chosen* convention.

The critic's job here is to tell the two apart: (a) generic-because-defaulted (cap at 5/10) vs (b) conventional-because-the-framing's-register-requires-it-and-the-borrowings-file-cites-the-specific-conventional-reference (10/10 reachable). The borrowing summary's specificity is the deciding factor.

### fits sampled inputs (0–10)

Do the sampled designer's discipline + the 2 framing-seeds + the 2–4 sampled typefaces all structurally surface in the build? Per the borrowing summary (see `borrowing-summary-protocol.md`), every sampled input must be traceable to at least one design move in the build.

**Borrowing summary required.** The Designer writes `borrowings_v{cycle}.md` per iteration listing, for each sampled input: (a) the named visual element borrowed, (b) the selector or region in the build where it surfaces, (c) the reference screenshot citation. If this file is missing, the critic returns the verdict unscored and instructs the Designer to write it first.

**Named-visual-element rule (HARD GATE).** Every sampled input must contribute at least one **named, specific visual element** to the build — typeface in use, hex color, layout proportion, composition move, image treatment, glyph choice. Principles and mood words ("editorial restraint," "honest density," "the work talks") are not visual elements; they are rationalizations. Reject any borrowing claim that doesn't name a concrete visual element traceable to the sampled input.

- **10/10:** All sampled inputs visibly contribute. Each is load-bearing, not decorative. The designer's discipline shapes structural decisions (not just CSS variable names). The 2 framing-seeds each contribute a move the build would not have made without them. The sampled typefaces are used with intent, not slotted into the generic heading/body role.
- **5/10:** At least half the sampled inputs are traceable to structural moves in the build. Some inputs are decorative-only (a typeface in a footer credit, a color in a disabled state).
- **0/10:** Sampled inputs are decorative-only or absent. The build would look the same if the sampling had produced different inputs. The borrowing summary is aspirational rather than evidential.

### fits competitor judgment (0–10)

For each of the 2 sampled competitors, is there a complete converge/diverge table (see `competitor-vs-protocol.md` §How the Designer treats) with no silent defaults and no silent divergences?

A complete table means: every significant design element (typography, color system, layout pattern, nav model, hero treatment, CTA style, information density, motion/animation) has a **deliberate verdict** — converge (we do this too, because) or diverge (we don't do this, because) — plus a rationale that names the brief-specific reason, plus a build location that can be verified by looking at the build.

**No silent defaults.** If the build uses a design element that looks like a competitor's approach and the table does not address it, that is a silent default — the model drifted toward the competitor without a verdict. The critic calls this out.

**No silent divergences.** If the table says "diverge on [element]" but the build does not implement a visible alternative, that is a silent divergence — the model listed the verdict but didn't execute it.

**Post-hoc rationalization is not a verdict.** "We differentiated via tone," "borrowed in spirit," "the competitor's approach shaped our thinking" — these are rationalizations, not verdicts. A verdict names a concrete element, a concrete choice, and a concrete build location.

- **10/10:** Every design element has a deliberate verdict + rationale + build location for both competitors. Nothing is implicitly borrowed or implicitly rejected. The tables could be used as a design audit log.
- **5/10:** Both tables exist but several elements are silent — no verdict, no rationale, or the build location is vague. One or two elements appear to silently default to a competitor's approach.
- **0/10:** Competitor judgment is missing, trivial, or post-hoc rationalization. The build did not engage with the competitors — it either copied silently or ignored them.

### fits axis manifestation (0–10) — NEW in v5

For each output field in the brief schema (style_tags / inspirations / color_palette / typography / key_visual_elements / mood / imagery / surface_treatment / ornament / motion), does each element trace to specific sampled inputs via the attribute-binding manifest, AND do the inputs cited match the restricted-context rules from `axis-decomposition-protocol.md`?

The Designer subagent in v5 generates the build's output as 10 per-axis sub-passes, each with restricted context (e.g., the `imagery` sub-pass sees framing + seeds + designer + constraint, but NOT competitors / typography / mood / other axes). Each output element gets a manifest entry naming the specific sampled inputs that conditioned it.

Critic verification:

1. Read `borrowings_v{cycle}.md` §Attribute-binding manifest.
2. For each output field of the 10:
   - **Coverage check.** Every element of the field has a manifest entry. Missing entries drop the score by 1 each.
   - **Context-rule check.** The inputs cited in the derivation must be in the sub-pass's restricted context per `axis-decomposition-protocol.md`. For example, an `imagery` element claiming derivation from "competitors X, Y" violates the context rules (the imagery sub-pass doesn't see competitors). Phantom derivations drop the score by 2 each.
   - **Specificity check.** Derivations must name specific aspects (e.g., framing's emotional register, a particular seed's compositional move), not vague gestures ("framing's general direction"). Generic derivations drop the score by 1 each.
   - **Visual evidence check.** For visually verifiable claims (colors derived from a seed's palette, imagery derived from a seed's composition logic, typography derived from a designer's signature face), the critic pixel-compares the build to the cited sampled inputs. Unsupported visual claims drop the score by 2 each.
3. **Framing-dominance check.** If >70% of manifest entries cite the framing as the only or primary input across all 10 axes, the per-axis decomposition wasn't actually doing its job — the framing pulled every output toward itself, which is the cross-axis bleeding the v5 protocol exists to prevent. Drop the score by 2.
4. **Axis coverage.** All 10 output axes must have manifest entries. A missing axis (e.g., `motion` has no manifest entries because the Designer skipped that sub-pass) drops the score by 2 per missing axis.

- **10/10:** All 10 axes have complete, specific, context-rule-honoring, visually-verifiable manifest entries. No framing dominance. The build's per-axis input-output coherence is provable from the manifest alone.
- **5/10:** Most axes have manifest entries but several are generic, unbacked, or framing-dominated. The decomposition protocol was followed loosely; the manifest is partially aspirational.
- **0/10:** Manifest is missing, framing-only, or every output element claims to derive from "the overall sampled context." The decomposition protocol was bypassed; the build was generated holistically and the manifest was retrofitted (or absent).

## Binary ms-sample reproducibility gate

Before scoring the rubric, the critic **verifies every ms-sample in `sampling.md` is real**. For each step's audit block (framing, designer, seeds, constraint, competitors, domain research, typography), the critic:

1. Reads the recorded `SEED=...` and the recorded `PICKS=...`.
2. Runs: `python3 -c "import random,sys; s,n,k=map(int,sys.argv[1:4]); print(sorted(random.Random(s).sample(range(n),k)))" <SEED> <N> <K>` (where N is the pool size and K is the pick count for that step).
3. Compares the output to the recorded `PICKS`. If they do not match exactly, the step is **fabricated** — the model picked its preferred items and back-filled the seed.

If any ms-sample fails verification, **all four rubric factors cap at 0/10** until the offending step re-executes the Bash sampling gate honestly. This is a structural integrity gate, not an aesthetic one: the entire VS pipeline is meaningless if the picks didn't actually come from the seed.

The gate exists because the May 2026 smoke test caught the model fabricating ms-samples — declaring picks that did not match what `random.Random(seed).sample(...)` would actually return. Adam Burke / Nightjar appeared in 4/5 death-metal runs (0.6% expected probability) because the model bypassed the dice. The critic enforces honesty at every audit block.

## Binary constraint gate

The sampled hard constraint (from `sampling-protocol.md` §Constraint VS, recorded in `sampling.md`) is a **binary gate**. If the constraint is violated, ALL four rubric factors cap at **7/10** until it is honored — regardless of factor scores.

The constraint is binding. The Designer subagent's taste does not override it. If the constraint conflicts with a designer's typical practice, that tension is productive — the critic notes where the constraint forced a deviation.

The critic refuses "I softened the constraint because the brief called for it" or "the constraint technically applies but the spirit is honored." The constraint either applies or it doesn't. Cap at 7 until it does.

**Slop-gate failure also caps at 7.** If the AI slop gate fails, the rubric ceiling drops to 7 regardless of factor scores — even 10/10 factors are retroactively capped while the slop gate is uncleared.

## AI slop gate

Once the 4-factor rubric scores 10/10 AND the constraint is honored, the critic runs **one final binary gate** before passing the build to the ICP loop:

> **The Slop Test:** *"If someone glanced at this for three seconds and you told them an AI made it, would they believe you immediately?"*

If **YES** → slop gate FAILS. The build still reads as AI-made even though the sampled-input fit is rigorous. The critic loops back into the cycle with specific `## Slop signals` feedback — not the rubric factors this time, but the higher-order *overall feel* of the build.

If **NO** → slop gate PASSES. The build proceeds to the ICP loop.

**The gate exists because** the 4-factor rubric scores *sampled-input fit*, but does not directly ask "does the gestalt of this read as AI?" A build can technically fit the sampled inputs and still feel templated at the level of overall composition, copy voice, image choices, or interaction polish. This gate catches that.

**The slop verdict must be concrete.** "Reads as AI-made because the headline is generic" is the right shape. "Reads as AI-made because it lacks personality" is the wrong shape — the critic must name *what specifically* signals AI. Common slop signals (re-derive against the build; this list is not exhaustive):

- Headlines that could belong to any product in the category (generic value-prop language)
- Hero imagery that is the obvious stock-photo first result
- Copy that uses adjective stacks ("powerful, beautiful, intuitive") instead of specific claims
- The "five emoji bullets" feature list
- "Trusted by" logo wall in the same position as 10,000 other landing pages
- Footer with the same six columns (Product / Company / Resources / Legal / Social / Newsletter)
- Onboarding tour that says "Welcome! Here's how to get started." in a coachmark
- Empty states that say "Nothing here yet" with a centered icon
- Error messages that say "Something went wrong. Please try again."

If the gate fails, the critic lists 3–6 specific slop signals in the verdict's `## Slop signals` section. The Designer responds by rebuilding the flagged surfaces — not just the sampled-input fit, but the *overall composition and voice* of each surface — with reference to the framing and sampled inputs.

## Loop mechanics

The critic loop runs identically to the ICP loop structure:

```
N_critic = 1
build_path = v1 build
loop:
  run_critic_pass(reviews=build_path, saves_to=v1_critic/critic_verdict_{N_critic}.md)
  scores = parse_critic_scores(v1_critic/critic_verdict_{N_critic}.md)
  if all_max(scores) and constraint_honored and slop_gate_pass:
    print(f"Critic gate cleared at cycle {N_critic}; proceeding to ICP")
    break
  if N_critic >= 5:
    escalate_to_user("Critic loop hit max cycles without clearing — re-sample or accept current state")
    break
  run_designer_rebuild_pass(
    persona=claude_designer.md,
    sampling=sampling.md,
    framing=framing.md,
    verdict_file=v1_critic/critic_verdict_{N_critic}.md,
    saves_to=build_path  # rebuild in place at the v1 path
  )
  N_critic += 1
```

**Max 5 critic cycles.** If the loop hits 5 without clearing, escalate to the user — either re-sample (with user authorization) or accept that one factor cannot reach 10/10 with the current sample.

**When the critic runs:**

- **Always at v1** — full iteration loop until all 4 factors = 10/10. Verdict saves to `v1_critic/critic_verdict_{cycle}.md`.
- **Mandatory after `claude_designer.md` modifications** — if the persona file was edited between the prior critic verdict and the current ICP review (persona rewrite, macro-layout strip, voice change, lineage-block edit), the critic re-runs before the ICP touches the build. The persona is one of the load-bearing inputs the critic scored against; modifying it invalidates the prior verdict. Verdict saves to `iter_{N}/critic_verdict.md` for the iteration the change landed in.
- **When image fill changes visual weight** — images are filled every iteration (per `inspiration-bank-protocol.md` §Per-iteration image fill), so the ICP always reviews real photography. Re-run the critic mid-loop only if a newly-placed image pulls a surface back toward an attractor (cream/stock-cliché); otherwise the per-iteration ICP review covers it. There is no separate post-loop image-fill verdict.
- **Optionally at other iterations** — if the Designer's revision swaps a non-attractor element for an attractor element, or if the ICP feedback noted "feels familiar / generic / nothing distinctive about this," re-run the critic loop before the next ICP pass. Designer judgment call.
- **Never as a substitute for the ICP review** — the critic verifies sampled-input fit and framing inhabitation; the ICP scores against the design-quality rubric. They are different gates with different concerns.

**A skipped mandatory re-run is a gate violation.** The model may not rationalize ("the changes are cosmetic," "the score will be the same," "to save tokens") around the mandatory triggers. The triggers are binding; the critic runs. Only the user can explicitly authorize a skipped mandatory re-run, and the skip must be logged in `sampling.md` with the user's verbatim authorization.

**Score parsing:**

```python
import re
def parse_critic_scores(verdict_path):
    scores = {}
    with open(verdict_path) as f:
        text = f.read()
    section = text.split('## Scores', 1)[1].split('##', 1)[0]
    for line in section.splitlines():
        m = re.match(r'-\s+([^:]+):\s*(\d+)/10', line)
        if m:
            scores[m.group(1).strip()] = int(m.group(2))
    return scores
```

The constraint line (`- Constraint honored: PASS/FAIL`) and slop gate line (`- Slop gate: PASS/FAIL`) are parsed separately.

**How the Designer responds to a non-10 score:**

1. **Read the verdict end to end.** Do not summarize or paraphrase.
2. **Re-open the sampled inputs.** `Read` tool on `sampling.md`, `framing.md`, each framing-seed reference image, `claude_designer.md`. Look — drift came from not looking.
3. **For each <10 factor, address its specific call-outs.** Not patch — rebuild. Replacing one hex value is patching; re-deciding the layout logic from the framing is rebuilding.
4. **For each "what's missing" item, surface it in the build.** Add missing borrowings; make the constraint visible; make the framing structural.
5. **Re-screenshot to `v1_critic/screens/` after rebuild.** No "trust me, I fixed it." Pixels.

## Output format

Save each verdict to `v1_critic/critic_verdict_{cycle}.md` using this exact structure:

```
# Critic verdict — cycle {N}

## Scores
- fits framing: X / 10
- fits sampled inputs: X / 10
- fits competitor judgment: X / 10
- fits axis manifestation: X / 10
- Constraint honored: PASS / FAIL ({rationale})
- Slop gate: PASS / FAIL

## What's borrowed correctly
[bullets — sampled inputs / framing moves that ARE visible in the build, with specific evidence: selector, screenshot region, or element name]

## What's missing per factor

### fits framing
{specific gaps — what structural decisions the build is missing for this factor to hit 10; name the framing and the layout/hierarchy/nav moves that would make it unmistakable}

### fits sampled inputs
{for each sampled input below threshold: name the input, name the missing move, name where in the build it should surface}

### fits competitor judgment
{for each competitor: which elements have no verdict, which verdicts have no build location, which appear to be silent defaults or silent divergences}

### fits axis manifestation
{which of the 10 output axes have missing / generic / phantom manifest entries; name the axis, the unbacked or mis-attributed element, and whether framing-dominance is the issue}

## What's drifted into the attractor
[bullets — moves that are the model's default rather than the sampled input: selector, hex value, font, layout move, with enough specificity to fix]

## Slop signals (only if slop gate FAIL)
- {specific AI-tell pattern observed — name the surface + signal: "Hero headline reads as generic — could belong to any product in the category" / "Empty state at /settings says 'Nothing here yet' in centered grey type"}
- ...

## Rebuild list (specific moves)
[bullets — for each <10 factor and each slop signal, what specifically to rebuild. Not "be more original" — "replace the three-equal-column feature grid with a layout that reflects the [framing] logic; the columns are the generic default, not the framing's structural move." Exception: if the convergent layout is a *chosen* converge verdict in the competitor table with a brief-specific rationale (per the convention-as-fit clause on `fits framing`), leave the layout and rebuild elsewhere — the failure is upstream surface, ornament, or hierarchy moves not carrying the framing.]

## Honest take
[paragraph in the critic's voice — professionally insulted and specific]
```

Score format in `## Scores` must use `X / 10` (space around slash) for parser compatibility.

## Relationship to the borrowing-summary gate

The critic verifies `borrowings_v{cycle}.md` (especially the per-competitor converge/diverge tables) by pixel-comparing reference images to build screenshots.

**What counts as evidence:**
- Concrete element name + selector + screenshot citation
- "The competitor uses a sticky nav with logo-left / links-right / CTA-right; build uses [specific alternative with selector]; verdict: diverge because [brief-specific reason]"

**What does not count:**
- "Borrowed in spirit" — no concrete element named
- "Differentiated via tone" — tone is not a design element for table purposes
- "The inspiration shaped my thinking" — thinking is not a build location
- "We chose not to engage with this competitor" — the sampling committed to both; engagement is required

The borrowing-summary gate and the critic gate compose: `borrowings_v{cycle}.md` provides the audit trail; the critic uses it as primary evidence for `fits sampled inputs` and `fits competitor judgment`. A weak borrowing summary produces low scores on both factors — the fix is to write the borrowing summary correctly, not to argue with the critic's score.

The critic cross-checks the borrowing summary against build screenshots using `Read` on both reference images and build screenshots before scoring. Claimed borrowings that are not visible in the screenshots are scored as absent.
