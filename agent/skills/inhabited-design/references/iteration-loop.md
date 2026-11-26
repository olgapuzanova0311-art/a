# Iteration loop protocol

File conventions, subagent prompt templates, and the loop logic for the inhabited-design skill.

## Directory structure

```
.inhabited/                 # all skill-generated files for this project live here (add to .gitignore)
  inhabited.md              # stable per-project context (teach gate) — survives across runs
  pipeline_status.md        # 14-step run progress (resume index)
  sampling.md               # seeded sample (framing + designer + seeds + constraint + competitors + domain refs + typography) — frozen at v1 except for iteration domain re-samples
  framing.md                # chosen framing and framing-seed refs
  claude_designer.md        # persona, generated in sampled practitioner's voice
  claude_icp.md
  claude_critic.md          # adversarial critic persona
  claude_anti_defaults.md   # research-derived AI-design tells for this project
  designer/
    index.html              # the latest build (each iteration's revision goes here)
  references/               # downloaded visual references (cumulative)
    01_linear_dashboard.png
    02_tracksmith_meter.jpg
    ...
    photos/                 # stock images (Unsplash/Pexels), filled at the end of each iteration
      01_unsplash_dawn-runner.jpg
      ...
  inspiration.md            # the bank (framing seeds + designer + competitors + domain refs + typography)
  v1_critic/
    critic_verdict_1.md     # first critic review of v1 (4-factor rubric)
    critic_verdict_2.md     # after first rebuild (if any factor < 10)
    ...                     # max 5 cycles
    screens/                # critic's viewport-bounded screenshots
  iter_1/
    runner_feedback.md      # ICP scores (7-factor rubric)
    designer/
      index.html            # revision based on iter 1's feedback (IMAGE_INTENT placeholders during build, filled from stock before the ICP review)
    references/             # any new references added this iteration
    critic_verdict.md       # only present if critic re-ran this iteration
  iter_2/
    runner_feedback.md
    designer/
      index.html
  ...
  final/                    # converged build (last iteration; real images already placed each iteration)
    index.html              # converged build with real photos in place
    runner_feedback.md      # final ICP review — already on real images (no separate post-fill pass)
```

Two loops in series:

- **Critic loop (v1):** Critic reviews v1 against the 4-factor rubric (see `adversarial-critic-protocol.md`); Designer rebuilds; repeats until all 4 = 10/10 AND constraint honored AND slop gate PASS (or max 5 cycles → escalate to user).
- **ICP loop:** ICP reviews against 7-factor design rubric; Designer revises; repeats until all factors = max.

---

## Loop 1 — Critic loop (bank fit)

The Critic loop runs once, on v1, before any ICP scoring. Its purpose is to gate out builds that have drifted into the cream/warm-editorial attractor or failed to surface the sampled inputs structurally — before the ICP scores them and risks awarding 10/10 to a build that inhabits the wrong aesthetic entirely.

### The 4-factor rubric

The critic scores against the 4-factor rubric defined in `adversarial-critic-protocol.md`. The rubric is not re-defined here; see that file for factor definitions, scoring guidance, and the named-visual-element rule. Summary only:

1. **fits framing (0–10)** — does the build structurally inhabit the chosen framing?
2. **fits sampled inputs (0–10)** — are the sampled designer's discipline + framing-seeds + typefaces all load-bearing in the build?
3. **fits competitor judgment (0–10)** — is there a complete converge/diverge table for each sampled competitor?
4. **fits axis manifestation (0–10)** — does each output axis trace to its restricted-context sampled inputs via the attribute-binding manifest?

Plus two binary gates: **Constraint honored (PASS/FAIL)** and **Slop gate (PASS/FAIL)**. Constraint failure caps all four rubric factors at 7. Slop gate only runs once the 4-factor rubric reaches 10/10/10/10 and constraint is PASS.

### Critic file convention

Each critic verdict saves to `v1_critic/critic_verdict_{cycle}.md`. Mid-loop re-runs (if drift is detected during ICP iterations) save to `iter_N/critic_verdict.md`.

### Loop mechanics

```
# Critic loop (runs once, on v1, before the ICP loop)
build_path = .inhabited/designer/index.html  # v1, built honoring sampling.md
cycle = 0
while True:
  cycle += 1
  if cycle > 5:
    escalate_to_user("Critic rejected 5x; sample may be unworkable — re-sample or accept stuck factor")
    break
  spawn_critic_subagent(
    persona=claude_critic.md,
    sampling=.inhabited/sampling.md,
    framing=.inhabited/framing.md,
    inspiration=.inhabited/inspiration.md,
    designer_persona=claude_designer.md,
    build=build_path,
    saves_to=v1_critic/critic_verdict_{cycle}.md
  )
  scores = parse_critic_scores(v1_critic/critic_verdict_{cycle}.md)
  if all_max(scores) and constraint_honored(verdict) and slop_passed(verdict):
    print(f"Critic gate cleared at cycle {cycle}; proceeding to ICP loop")
    break
  if stuck_3_cycles_on_same_factor(scores):
    ask_user_about_stuck_factor()
  spawn_designer_subagent_rebuild(
    persona=claude_designer.md,
    sampling=.inhabited/sampling.md,
    framing=.inhabited/framing.md,
    verdict=v1_critic/critic_verdict_{cycle}.md,
    build=build_path,
    saves_to=build_path  # rebuild in place
  )
```

**Max 5 critic cycles.** If the loop hits 5 without all 4 factors reaching 10/10, the constraint clearing, and the slop gate passing, escalate to the user. Either the sample is unworkable (re-sample with user authorization) or one factor cannot reach 10/10 with the current inputs (accept and document the stuck factor). Do not run a 6th cycle silently.

**When the critic runs mid-ICP-loop.** If the Designer's revision during the ICP loop swaps a non-attractor element for an attractor element — or if ICP feedback notes "feels familiar / generic / nothing distinctive" — optionally re-run the critic loop. The mid-loop critic saves to `iter_N/critic_verdict.md`. If any factor scores below max, the Designer rebuilds before the next ICP pass.

---

## Loop 2 — ICP loop (design quality)

The ICP loop runs only after the Critic gate AND the State-coverage gate have both cleared. The ICP scores the design quality of the build using the 7-factor rubric defined in `scoring-rubric.md`.

### 7-factor design rubric

Rubric definition is in `scoring-rubric.md`. The ICP scores each factor 0–10. All factors must reach max before the loop converges. The ICP does not run the 4-factor bank-fit check — that is the Critic's gate. If drift is suspected during the ICP loop, re-run the Critic mid-loop.

### Loop mechanics

```
# ICP loop (runs only after critic gate AND state-coverage gate clear)
N = 1
loop:
  spawn_icp_subagent(
    persona=claude_icp.md,
    build=build_path,
    saves_to=iter_N/runner_feedback.md
  )
  scores = parse_scores(iter_N/runner_feedback.md)
  if all_max(scores):
    print(f"Done — perfect scores at iter {N}")
    break
  if stuck_3_iters(scores):
    ask_user_about_stuck_factor()
  spawn_designer_subagent(
    persona=claude_designer.md,
    sampling=.inhabited/sampling.md,
    framing=.inhabited/framing.md,
    prev_build=build_path,
    prev_bank=.inhabited/inspiration.md,
    feedback=iter_N/runner_feedback.md,
    saves_to=iter_N/designer/index.html
  )
  build_path = iter_N/designer/index.html
  # Optional: re-run critic if revision drifted back toward attractor
  if drift_suspected(iter_N/runner_feedback.md, iter_N/designer/index.html):
    spawn_critic_subagent(..., saves_to=iter_N/critic_verdict.md)
    if any_factor_below_max: spawn_designer_subagent_rebuild(...)
  N += 1
```

The ICP writes feedback to `iter_N/runner_feedback.md` using the 7-factor rubric structure. Score parsing follows the same `## Scores` block format as the Critic — see Score parsing section at the end of this file.

---

## Domain re-sample at iteration boundaries

This is the single sampled input that can grow during the build. All other sampled inputs (framing, designer, framing-seeds, constraint, competitors, typography) are fixed at the start and do not change during iterations. Domain research is the exception.

**The rule:** During critic-loop and ICP-loop iterations, the Designer may request +2 additional domain references per iteration, up to a cap of +6 total across all iterations of both loops combined. The original 2 domain refs from the initial sample are never replaced — iteration additions are strictly additive.

### How additions work

1. Designer identifies a specific gap in the current domain bank — a design element or register that iteration feedback has flagged and that the original 2 domain refs do not cover.
2. Designer requests the addition via VS, stating the justification (see Justification requirement below).
3. VS procedure: brainstorm 20 fresh domain reference candidates conditioned on the specific gap, assign band tags using the 4/8/8 spread (canonical / mid-tier / long-tail), draw 2 uniformly via the **external sampling gate** (see `sampling-protocol.md` §The external sampling gate):

```bash
python3 -c "import random,time,sys; n,k=int(sys.argv[1]),int(sys.argv[2]); s=int(time.time()*1000); print(f'SEED={s}'); print(f'PICKS={sorted(random.Random(s).sample(range(n),k))}')" 20 2
```

The Bash stdout's `PICKS=[i, j]` line is the only source of truth; the model does NOT compute the picks internally. Record command + stdout + resolved picks in `sampling.md`.

4. Present the full 20-entry pool, the Bash command + stdout, the two chosen entries, and a brief justification tying each chosen ref to the specific gap. User confirms via the standard four-action flow (continue / resample / choose N, M / new options).
5. In auto mode, the present-confirm step is skipped per the standard auto rules (see `sampling-protocol.md` §Auto mode); the agent fires through logging the picks to `sampling.md`.

For the full re-sample procedure, see `domain-research-vs-protocol.md` §Iteration re-sample rule.

### Caps

| Constraint | Value |
|---|---|
| Max additions per iteration | +2 (one VS draw of 2) |
| Max additions across all iterations (critic + ICP loops combined) | +6 |
| Max domain refs in bank at any point | 8 (original 2 + up to +6) |

### Justification requirement

When the Designer requests an iteration addition, they must state **which specific piece of iteration feedback motivated it** — concrete and traceable. The Critic verifies that the cited gap exists in the prior cycle's feedback before allowing the addition to proceed.

**Accepted justification format:**

> "I need a warmer empty-state reference because ICP iteration 2 said the empty state felt cold — specifically, the `zero-results` panel was described as clinical. I want to sample 2 domain refs from the material/texture end of the pool to find a register that changes this."

This justification names: (a) the design element (empty state / zero-results panel), (b) the specific feedback (ICP iteration 2, "felt cold / clinical"), and (c) the direction for the new sample (material/texture register).

**Rejected justification:**

> "I want to add references because the build feels thin."

No specific iteration feedback is cited. No design element is named. No gap is traceable. The Critic must refuse this request and instruct the Designer to identify the specific element and the specific feedback cycle that exposed the gap.

**The acceptance standard:** Could a reader of `sampling.md` trace this addition to a specific critic or ICP feedback comment? If yes, the justification is valid. If no, it is not.

### Audit trail

Each iteration addition gets its own section in `sampling.md` using this title format:

```
## Domain re-sample — iteration {N}
```

The section records:
- Which loop and cycle triggered the addition (e.g., "ICP loop iteration 2")
- The specific gap that motivated the addition (verbatim from the Designer's justification)
- The full 20-entry pool for this draw (with band tags)
- The ms-clock seed used
- The two chosen indices and the two chosen domain references
- The user confirmation action (interactive mode) or `mode: auto` (auto mode)
- Critic verification: confirmation that the cited gap exists in the cited feedback file

Rejection is a valid outcome. If the user declines the addition — or the Critic determines the justification does not trace to a specific feedback gap — the addition is declined and no new ref enters the bank. The declined request is still logged in `sampling.md` with the reason for rejection. The Designer must not re-propose the same addition in the same iteration.

---

## State-coverage gate

Between the Critic loop converging and the ICP loop starting, the build must demonstrate that **every required state** is designed and screenshotted — not just the happy path. The ICP's 7-factor rubric (per `scoring-rubric.md`) is aesthetic-quality oriented; a build with no empty state defined can still get 10/10 because the ICP scores what they *see*, not what's *missing*. This gate catches that.

### Required states (the floor)

For every distinct surface in the build, the Designer must produce viewport-bounded screenshots of:

1. **Default / happy path** — content present, normal flow
2. **Empty state** — no data yet, first-run, before content is created
3. **Loading state** — fetch in progress, optimistic UI or skeleton, NOT just a spinner alone
4. **Error state** — fetch failed, validation failed, permission denied (NOT just "Something went wrong"; the message must teach the user what to do next)
5. **First-run / onboarding** — what the user sees the very first time they open this surface
6. **Overflow / edge case** — long text, very many items, no permissions, etc. — whatever the surface's specific edge looks like

Not every surface needs all six. The Designer judges which apply per surface — but **must explicitly list** which states are required and which are not, in `states_v{cycle}.md` in `.inhabited/`. "Not applicable because …" is a valid entry; "I forgot about this state" is not.

### Verifiable condition

The gate clears when, for every surface:
- `iter_{cycle}_states/screens/<surface>_default.png` exists AND was Read
- One of `iter_{cycle}_states/screens/<surface>_<state>.png` exists for each required state, AND was Read
- `states_v{cycle}.md` lists each surface, each required state, each NOT-APPLICABLE marker with reason, AND each screenshot file path

Use the bounded-screenshot pattern (see Pixel verification gate below): `browser_resize 1280 800` → `browser_take_screenshot filename=...` → `Read` the file.

### What does NOT count

- **A spinner alone** as the loading state — the Designer must design a loading state that's a real composition (skeleton screen with brand-tinted skeletons, optimistic placeholders, a sentence that's intentional)
- **"Nothing here yet" centered with a generic icon** as the empty state — the empty state must teach the interface
- **"Something went wrong" as the error message** — the error message must name what failed and how to recover
- **Skipping first-run as "covered by onboarding tour"** — the surface's own first-impression matters even when an onboarding tour exists
- **A README that says "this state would look like X" with no actual rendered design** — must be in the build, screenshotted, Read

### How the gate runs

Spawn a state-coverage subagent (or the Designer in state-pass mode) with:

```
First, read /path/to/claude_designer.md. Embody the persona fully.

The critic gate has cleared. Before the ICP loop starts, your job is the state-coverage gate. Read /path/to/v1_critic/critic_verdict_{final}.md and /path/to/inspiration.md to confirm what shipped. Then walk the build and, for every distinct surface (every URL, every key component, every interactive state-changing element):

1. List the surfaces in /path/to/states_v{cycle}.md.
2. For each surface, determine which of the six required states apply: default, empty, loading, error, first-run, overflow.
3. For each applicable state that does not yet exist in the build, design and implement it. Re-open the inspiration bank. The empty state's composition is borrowed from the bank just like the default state — same discipline.
4. For each NOT-applicable state, write a one-line rationale in states_v{cycle}.md.
5. For each implemented state, capture a bounded screenshot at iter_{cycle}_states/screens/<surface>_<state>.png and Read it.

Constraints:
- No "Nothing here yet" empty states. No "Something went wrong" errors. No spinner-only loading states.
- Each state must trace a borrowing line in states_v{cycle}.md — what reference in the inspiration bank it's borrowing from for composition, voice, and treatment.
- The sampled hard constraint is still in effect; `claude_anti_defaults.md` still binding.

When done, return summary (under 200 words) listing each surface and the states added or marked NOT-APPLICABLE with reasons.
```

After the subagent finishes, verify `ls iter_{cycle}_states/screens/` and `states_v{cycle}.md` exist and are complete. If `states_v{cycle}.md` still has `TODO` or `…` markers, re-spawn until they're resolved.

### Why this gate exists

A previous failure mode: a build cleared the Critic loop with 10/10/10/10 bank fit, then the ICP scored it 10/10 on all seven aesthetic factors based on the default state alone. After shipping, the user hit an empty state on first run and got centered "Nothing here yet" placeholder text in a generic grey. The ICP never saw it because it never reviewed empty states. The state-coverage gate forces every state to be designed *before* the ICP scores, so the ICP's review covers the whole product, not just the happy path.

---

## Pixel verification gate (Jesse Vincent gate)

DOM-only review misses entire classes of visual bugs: `overflow: hidden` not clipping `display: inline` parents, sticky-position collisions, z-index overlaps, cropped images (object-fit failures), invisible focus rings against busy borders, marker overlays eating body text, layout asymmetries, color contrast at rendered scale.

The skill empirically discovered this in May 2026 when an ICP review gave seven 10/10 scores to a build that had five visible P0 bugs the DOM snapshot couldn't see.

**Both subagents — ICP and Designer — must clear the pixel gate at iteration startup.**

### Iteration startup gate (BLOCKING)

> **Trigger:** Starting this review (ICP) or about to return "build done" (Designer).
> **Condition:** At least one viewport-bounded screenshot exists at `iter_{N}/screens/` (ICP) or `iter_{N}/designer/screens/` (Designer) for each key surface you intend to score against or ship.
> **Next action:** Scoring (ICP) or returning the summary (Designer) is BLOCKED until the condition is met.

### Bounded-screenshot pattern

```bash
mkdir -p iter_{N}/screens
```

Then, for each key screen, in this exact order:

1. **Bound the viewport first** — `browser_resize 1280 800` (or smaller; never larger than 1280 on the longest edge). This caps the saved file under the 2000px Read-tool limit.
2. **Capture to disk** — `browser_take_screenshot filename=iter_{N}/screens/<descriptive_name>.png`. ALWAYS use `filename`. NEVER `fullPage: true` (can exceed 2000px even at small viewport).
3. **Read the saved screenshot** — `Read` tool on the file path. Look at the pixels. Note what the DOM cannot tell you.
4. **`browser_snapshot`** — for DOM accessibility tree (text content, structure, semantic landmarks).
5. **`browser_evaluate`** — for computed styles where DOM text isn't enough (e.g., to verify a hex value or font-family rule).

### Why bounded screenshots, not banned screenshots

The original protocol banned `browser_take_screenshot` because it dumps images into conversation context and can break Read with the 2000px limit. The band-aid created a worse failure mode (silent visual regressions). The correct guard is to **bound the viewport at capture time** so the saved file is well under the limit, and **read the file from disk**, not from in-context image content. `filename=` parameter writes to disk; the captured response can be discarded. Viewport-bounded PNG files are 100–300KB and Read fine.

---

## Slop signals format

The AI-slop gate's failure feedback writes a `## Slop signals` section in the critic verdict. Each entry names a specific surface plus a specific pattern observed. The section appears only when `Slop gate: FAIL`.

Common slop signal patterns (re-derive against the actual build; this list is not exhaustive):

- Headlines that could belong to any product in the category — generic value-prop language not anchored to this specific product, audience, or domain
- Hero imagery that is the obvious stock-photo first result — the most-shot angle, the most-licensed face, the canonical composition for the category
- Copy that uses adjective stacks ("powerful, beautiful, intuitive") instead of specific claims — description by mood rather than function
- The "five emoji bullets" feature list — emoji before every list item as a substitute for visual design
- "Trusted by" logo wall in the same position as 10,000 other landing pages — social proof as default layout block rather than deliberate element
- Footer with the same six columns (Product / Company / Resources / Legal / Social / Newsletter) — the structural template surfacing through the design
- Onboarding coachmark that says "Welcome! Here's how to get started." — the AI-default first-run message
- Empty states that say "Nothing here yet" with a centered icon — uncommissioned placeholders instead of designed states
- Error messages that say "Something went wrong. Please try again." — the model's default error template rather than a designed error

When the slop gate fails, the Designer rebuilds the flagged surfaces — **composition and voice, not just bank fit**. The critique is at the gestalt level: even when the sampled inputs are technically present, the overall feel reads as templated. The fix is to make the framing structural in each flagged surface, not to re-verify the borrowing summary.

---

## Subagent prompt templates

### Critic subagent prompt

```
First, read /path/to/claude_critic.md. Embody the persona fully from your next response. No persona summary. No breaking character to be charitable.

You are running cycle {cycle} of the v1 critic gate for {{App X}} (or iteration {N}, if running mid-loop). The current build is at:
/path/to/build/index.html

(Previous critic verdict at /path/to/v1_critic/critic_verdict_{cycle-1}.md scored {prev_scores}. The designer addressed {summary_of_rebuild}.)

## Read in this order

1. /path/to/sampling.md — the seeded picks (framing, designer, framing-seeds, constraint, competitors, domain refs, typography) the Designer was supposed to honor
2. /path/to/framing.md — the chosen framing and framing-seed references
3. /path/to/claude_designer.md — the Designer persona; you need to know what discipline should have surfaced
4. /path/to/inspiration.md — the assembled reference bank. Read the "borrowing X from this" lines.
5. /path/to/claude_anti_defaults.md — the research-derived AI-design tells for this project
6. For each reference in inspiration.md: `Read` the saved image file. You score against what's actually in the bank, not from memory.

## CRITICAL — pixel-and-DOM discipline

The framing attractor and cream-editorial attractor are *visual* attractors — you cannot catch them from DOM alone. Capture viewport-bounded screenshots and Read them before scoring.

### Critic startup gate (BLOCKING)

> **Trigger:** Starting this review.
> **Condition:** At least one viewport-bounded screenshot exists at `v1_critic/screens/` (or `iter_N/critic/screens/` if mid-loop) for each key surface you intend to score.
> **Next action:** Scoring is BLOCKED until the condition is met.

```bash
mkdir -p v1_critic/screens
```

Then, for each key surface:

1. `browser_resize 1280 800` (or smaller; never larger than 1280 on the longest edge).
2. `browser_take_screenshot filename=v1_critic/screens/<descriptive_name>.png`. ALWAYS `filename`. NEVER `fullPage: true`.
3. `Read` the saved file. Look at the pixels. The attractor is visible there.
4. `browser_snapshot` for DOM/accessibility.
5. `browser_evaluate` for computed styles where needed.

## Score against the 4-factor rubric

Score the build against the 4-factor rubric defined in `adversarial-critic-protocol.md`:

1. **fits framing (0–10)** — does the build structurally inhabit the chosen framing? Would someone cold to the brief name the framing within 30 seconds?
2. **fits sampled inputs (0–10)** — are the sampled designer's discipline + framing-seeds + typefaces all load-bearing in the build? Check `borrowings_v{cycle}.md` (required). Named-visual-element rule is a hard gate — reject any borrowing claim that names only a principle.
3. **fits competitor judgment (0–10)** — is there a complete converge/diverge table for each sampled competitor, with no silent defaults and no silent divergences?
4. **fits axis manifestation (0–10)** — does each output axis (style_tags / inspirations / color_palette / typography / key_visual_elements / mood / imagery / surface_treatment / ornament / motion) trace to the specific restricted-context sampled inputs it was allowed to see, via the attribute-binding manifest in `borrowings_v{cycle}.md`? Phantom derivations (citing inputs the sub-pass could not see) and framing-dominance (framing cited in >70% of entries) drop the score.

**Plus binary gates:**
- **Constraint honored (PASS/FAIL):** Read the sampled constraint from `sampling.md`. Honored without rationalization? Violation caps all four rubric factors at 7.
- **Slop gate (PASS/FAIL):** Run only once the 4-factor rubric is 10/10/10/10 AND constraint is PASS. "If someone glanced at this for three seconds and you told them an AI made it, would they believe you immediately?" YES = FAIL.

For the full rubric definitions and scoring guidance, see `adversarial-critic-protocol.md`.

## Score honestly

Withhold 10/10 from anything that hasn't earned it. Each <10 factor must have specific "what's missing" notes naming the missing framing move, the missing borrowed element, the silent default, or the unresolved competitor verdict. Save to /path/to/v1_critic/critic_verdict_{cycle}.md.

Use this EXACT structure (scores section format must match for parsing):

```
# Critic verdict — cycle {cycle}

## Scores
- fits framing: X / 10 — [what's missing or why it's 10]
- fits sampled inputs: X / 10 — [what's missing or why it's 10]
- fits competitor judgment: X / 10 — [what's missing or why it's 10]
- fits axis manifestation: X / 10 — [what's missing or why it's 10]
- Constraint honored: PASS / FAIL — [evidence]
- Slop gate: PASS / FAIL — [if FAIL, brief reason; details in Slop signals section]

## What's borrowed correctly
[bullets — sampled inputs / framing moves that ARE visible in the build, with specific evidence]

## What's missing per factor

### fits framing
{specific gaps — what structural decisions the build is missing for this factor to hit 10}

### fits sampled inputs
{for each sampled input below threshold: name the input, name the missing move, name where in the build it should surface}

### fits competitor judgment
{for each competitor: which elements have no verdict, which verdicts have no build location, which appear to be silent defaults or silent divergences}

### fits axis manifestation
{which of the 10 output axes have missing / generic / phantom manifest entries; name the axis, the unbacked or mis-attributed element, and whether framing-dominance is the issue}

## What's drifted into the attractor
[bullets — moves that are the model's default rather than the sampled input. Specific: selector, hex value, font, layout move.]

## Slop signals (only present if Slop gate: FAIL)
- {specific surface + signal: "Hero headline reads as generic — could belong to any product in the category"}
- ...

## Rebuild list (specific moves)
[bullets — for each <10 factor and each slop signal, what specifically to rebuild. Not "be more original" — concrete direction.]

## Honest take
[paragraph in your voice]
```

Note: Score format must use `X / 10` (space around slash) for parser compatibility.

When done, return a brief summary (under 100 words) including all factor scores AND the slop verdict.
```

### Designer rebuild prompt (responding to critic verdict)

```
First, read /path/to/claude_designer.md. Embody the persona fully.

The adversarial critic scored your build below 10/10 on at least one factor. Read /path/to/v1_critic/critic_verdict_{cycle}.md end to end. Do NOT summarize or paraphrase.

Then:
1. `Read` /path/to/sampling.md and /path/to/framing.md. Look at each picked entry. The low scores came from drift away from these picks.
2. For each reference the critic said you did not honor, `Read` the saved image file in /path/to/.inhabited/references/. Look. Then borrow specifically.
3. For each <10 factor, address its specific "rebuild list" items. Not patch — rebuild. Replacing one hex value is patching; re-deciding the layout logic from the framing and sampled inputs is rebuilding.
4. For each "what's missing" item, surface it in the build. Make the missing borrowings visible. Make the constraint visible. Make the framing structural. Make the sampled designer's discipline structural.
5. For each competitor with an incomplete converge/diverge table, complete the table — every significant design element, a deliberate verdict, a rationale, a build location.
6. Re-screenshot to /path/to/v1_critic/screens/ after rebuild (`browser_resize 1280 800` → `browser_take_screenshot filename=...` → never fullPage: true).
7. Save the rebuilt build to /path/to/.inhabited/designer/index.html (overwrite).

**Domain re-sample option:** If the critic's feedback reveals a gap in the inspiration bank — a register, texture, or material reference that your current 2 domain refs do not cover — you may request +2 additional domain refs via VS, subject to the cap (+6 total across all iterations). State the specific gap: which design element, which feedback cycle, why the current bank doesn't address it. See `domain-research-vs-protocol.md` §Iteration re-sample rule for the procedure.

Constraints: build with `IMAGE_INTENT` placeholders, then **fill every placeholder from stock (Unsplash/Pexels only — no AI generation, no other providers) at the end of the rebuild**, per `inspiration-bank-protocol.md` §Per-iteration image fill, so the critic (and the first ICP review of v1) see real images. Carry unchanged slots' images forward; re-source only changed slots. The sampled hard constraint is still in effect — honor it.

When done, return a summary (under 200 words) describing what you rebuilt for each <10 factor and how the sampled inputs and framing are now visible in the build.
```

### ICP subagent prompt

```
First, read /path/to/claude_icp.md. Embody the persona fully from your next response. No persona summary, no breaking character.

You are reviewing iteration {N} of {{App X}} ("{{App X name}}"). The current build is at:
/path/to/build/index.html

(Previous review at /path/to/iter_{N-1}/runner_feedback.md scored {prev_scores}. The designer addressed {summary_of_changes}.)

## CRITICAL — pixel-and-DOM discipline (the most important constraint in this prompt)

This is a visual design review of a live build. Your feedback **must be grounded in actual rendered pixels AND DOM state** — both. DOM-only review (browser_snapshot + browser_evaluate alone) misses entire classes of bug: `overflow: hidden` not clipping `display: inline` parents, sticky-position collisions, z-index overlaps, cropped images (object-fit failures), invisible focus rings against busy borders, marker overlays eating body text, layout asymmetries, color contrast at rendered scale. The skill empirically discovered this in May 2026 when an ICP review gave seven 10/10 scores to a build that had five visible P0 bugs the DOM snapshot couldn't see.

### Iteration startup gate (BLOCKING — Jesse Vincent gate pattern)

> **Trigger:** Starting this review.
> **Condition:** At least one viewport-bounded screenshot exists at `iter_{N}/screens/` for each key screen you intend to score against.
> **Next action:** Scoring is BLOCKED until the condition is met.

```bash
mkdir -p iter_{N}/screens
```

Then, FOR EACH key screen, in this exact order:

1. **Bound the viewport first** — `browser_resize 1280 800` (or smaller; never larger than 1280 on the longest edge).
2. **Capture to disk** — `browser_take_screenshot filename=iter_{N}/screens/<descriptive_name>.png`. ALWAYS use `filename`. NEVER `fullPage: true`.
3. **Read the saved screenshot** — `Read` tool on the file path. Look at the pixels.
4. **`browser_snapshot`** — for DOM accessibility tree.
5. **`browser_evaluate`** — for computed styles where needed.

**Verifiable condition before scoring:** `ls iter_{N}/screens/*.png` returns at least one file per screen, AND your feedback document cites specific pixel observations from those files.

**Enumerate the screens you snapshot in your review.** For this iteration:
{{ENUMERATED_LIST_OF_SCREENS_TO_SNAPSHOT}}

Open the current build in a real browser. file:// is blocked by Playwright; spin up python's http.server on a free port if needed. Actually USE the app — seed realistic data, exercise key flows, click around.

Then write a feedback document. SAVE to /path/to/iter_{N}/runner_feedback.md.

Use this EXACT structure (scores section format must be exact for parsing):

```
# {{ICP name}} feedback iteration {N}

## Scores
- {{Factor 1}}: X/10 — [what's missing or why it's 10]
- {{Factor 2}}: X/10 — [...]
- ...

## What's nice
[bullets]

## What got in the way
[bullets]

## Improvements I'd want next
[bullets — be specific]

## Honest take
[paragraph]
```

Score honestly. Don't withhold 10/10 to seem critical, but don't be charitable either. ~700–900 words.

When done, return brief summary (under 100 words) including all factor scores.
```

### Designer revision prompt (ICP loop)

```
First, read /path/to/claude_designer.md. Embody the persona fully. No persona summary, no breaking character.

The user reviewing your work is *exactly your target user*. Their feedback is voice-of-the-customer.

Read in order:
1. The implementation spec: /path/to/spec.md
2. Your previous build: /path/to/{prev_iter}/designer/index.html (or .inhabited/designer/index.html if N=1)
3. Your previous inspiration bank: /path/to/.inhabited/inspiration.md
4. Reference folders (existing images you can re-open):
   - /path/to/.inhabited/references/
   - /path/to/iter_*/references/  (any prior iteration's added refs)
5. The ICP's latest feedback: /path/to/iter_{N}/runner_feedback.md

The scores were {prev_scores}. {factors_at_max} are at max. {factors_below_max} need to climb. Read the ICP's "what's missing" notes carefully.

**Reference reuse:** The references in earlier folders are yours — REUSE them. Read those existing image files (Read tool) before each major design decision. Add new ones only if the feedback opens directions your existing bank doesn't cover. Save any new ones to /path/to/iter_{N}/references/ via curl + Pillow downscale to ≤1600px, png/jpg/jpeg/gif/webp only.

**Domain re-sample option:** If the ICP's feedback reveals a gap in the inspiration bank that your current domain refs do not cover — a specific element flagged in this feedback that no domain ref addresses — you may request +2 additional domain refs via VS. You must state the specific gap (which element, which ICP feedback cycle, why the current bank doesn't address it), and the Critic verifies the gap exists in the ICP feedback before the addition is allowed. Cap: +6 total domain ref additions across all iterations. See `domain-research-vs-protocol.md` §Iteration re-sample rule.

Update /path/to/iter_{N}/inspiration.md (or amend the parent inspiration.md with a "what changed in iter N" note).

Save the revised build to /path/to/iter_{N}/designer/index.html.

### Pre-handoff pixel-verification gate (BLOCKING — Jesse Vincent gate pattern)

> **Trigger:** You are about to return your "build done" summary.
> **Condition:** At least one viewport-bounded screenshot exists at `iter_{N}/designer/screens/` for each major section of the build you just shipped, AND you have Read each one.
> **Next action:** Returning the summary is BLOCKED until the condition is met.

**Concretely, after writing the build:**

1. `mkdir -p iter_{N}/designer/screens`
2. Spin up a local http.server in the build directory.
3. `browser_resize 1280 800` (or smaller). NEVER larger than 1280 on longest edge.
4. `browser_navigate` to the build.
5. For each major section (hero, load-bearing diagram, every interactive surface, comparison/data section, footer): `browser_take_screenshot filename=iter_{N}/designer/screens/<section>.png`. NEVER `fullPage: true`.
6. Capture each interactive state at hover and focus-visible (1 screenshot per state).
7. Mobile pass: `browser_resize 375 800`, screenshot the same sections.
8. **Read each saved screenshot** with the Read tool. Look at the pixels. Verify each section renders as intended — overflow clipping works, sticky positioning behaves, hover/focus states look intentional, no element collisions, no cropped images, no marker overlays eating body text.
9. ALSO `browser_snapshot` + `browser_evaluate` for text content and computed styles where needed.

### Other constraints

- The spec's no-external-assets-at-runtime rule still applies.
- Build with `IMAGE_INTENT` placeholders (correct dimensions/aspect + encoded subject/mood/treatment), then **fill every placeholder from stock (Unsplash/Pexels only — no AI generation, no other providers) at the end of this revision, before the pixel gate**, per `inspiration-bank-protocol.md` §Per-iteration image fill. The ICP reviews this revision with real images in place. Carry unchanged slots' images forward; re-source only slots whose layout/palette/intent changed.

Decide and ship. When done, return summary (under 250 words) in your persona's voice: which references you re-opened, what landed for each underscored dim, what you decided NOT to do.
```

---

## Score parsing

Both ICP and Critic verdicts use a `## Scores` block and the same parser:

```python
import re

def parse_scores(feedback_path):
    scores = {}
    with open(feedback_path) as f:
        text = f.read()
    section = text.split('## Scores', 1)[1].split('##', 1)[0]
    for line in section.splitlines():
        m = re.match(r'-\s+([^:]+):\s*(\d+)\s*/\s*10', line)
        if m:
            scores[m.group(1).strip()] = int(m.group(2))
    return scores

def constraint_honored(feedback_path):
    with open(feedback_path) as f:
        text = f.read()
    section = text.split('## Scores', 1)[1].split('##', 1)[0]
    for line in section.splitlines():
        m = re.match(r'-\s+Constraint honored:\s*(PASS|FAIL)', line)
        if m:
            return m.group(1) == 'PASS'
    return False

def slop_passed(feedback_path):
    """The Critic's final binary gate. Returns True if Slop gate: PASS,
    False if FAIL, and True if blank (gate hasn't run yet — rubric/floor failure will catch it)."""
    with open(feedback_path) as f:
        text = f.read()
    section = text.split('## Scores', 1)[1].split('##', 1)[0]
    for line in section.splitlines():
        m = re.match(r'-\s+Slop gate:\s*(PASS|FAIL)', line)
        if m:
            return m.group(1) == 'PASS'
    return True  # blank — gate hasn't run; rubric/floor failure will re-trigger cycle
```

The Critic's verdict uses `X / 10` (with spaces around the slash); the regex above handles both `X/10` and `X / 10`. Constraint and slop gate lines are parsed separately as binary gates. The ICP verdict uses `X/10` (no spaces).

---

## Common pitfalls

| Pitfall | Fix |
|---|---|
| Subagent fights over Playwright | Spawn ICP and Designer sequentially, not in parallel within a single iteration. |
| Image dimension errors mid-loop | Persona file enforces downscaling. See `file-size-guards.md`. |
| ICP gives charitable scores | Persona file says "honest, not charitable, withhold if not earned." |
| Loop stuck on one factor | Three stuck iterations → ask user about that factor. |
| Designer ignores feedback | Prompt instructs them to read every word of feedback file carefully. Verify by checking the revision summary. |
| Designer leaves `IMAGE_INTENT` placeholders unfilled at handoff | Fill from stock (Unsplash/Pexels) at the end of every iteration, before the ICP reviews — the ICP must see real images. |
| Designer reaches for AI generation or another stock source | Stock only, Unsplash/Pexels only. No generation, no Pixabay/other providers. |
| Critic gate skipped to "save tokens" | The critic gate is the framing/attractor interrupter. Skipping it lets the ICP score the trained cliché. Always run at v1. |
| Critic gives 10/10 charitably | Critic persona is uncharitable by design. Regenerate `claude_critic.md` from `adversarial-critic-protocol.md` if charity has crept in. |
| Designer "fixes" critic call-outs by patching hex values | Critic's next cycle catches this — they score the whole build. The Designer must rebuild moves, not patch tokens. |
| `sampling.md` not written before Designer persona generated | Hard gate. No persona, no design code, before `sampling.md` exists with all VS picks recorded. |
| Critic loop runs >5 cycles without converging | Escalate to user. Either the sample is unworkable, or one factor cannot reach 10/10 with the current inputs. Do not run a 6th cycle. |
| Domain ref requested without specific gap | Reject the request. Designer must name the specific element + specific feedback cycle. "The build feels thin" is not a gap. |
| Domain ref cap exceeded | Cap is +6 additional across all iterations. Track the count in `sampling.md`. Stop at 8 domain refs total. |
| Critic verifies gap from wrong feedback file | Critic must check the *cited* feedback file — the specific ICP or critic cycle the Designer named — not the most recent cycle. |
