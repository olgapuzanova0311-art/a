# Sampling protocol

Verbalized Sampling at every input. Every pick traces to a millisecond-clock RNG seed + a candidate enumeration logged in `sampling.md`. Any reader can replay `random.Random(seed).sample(range(N), K)` to verify.

## Per-step protocol files

| VS step | Protocol file |
|---|---|
| Framing | `framing-protocol.md` |
| Designer | `designer-vs-protocol.md` |
| Seeds | `seeds-vs-protocol.md` |
| Constraint | this file, §Constraint VS |
| Competitors | `competitor-vs-protocol.md` |
| Domain research | `domain-research-vs-protocol.md` |
| Typography | `typography-vs-protocol.md` |

## The millisecond-clock RNG seed

Every sampling step opens a fresh seed from `int(time.time() * 1000)`. The seed is one-time-use; the gate against re-rolls is `sampling.md` itself — once a pick is written, the step is closed. Re-rolls require an explicit user action (`resample` or `choose N`), itself logged.

## The external sampling gate (NON-NEGOTIABLE)

**The model does not run `random.Random(seed).sample(...)` in its own context. Ever.** Every ms-sample executes through the Bash tool; the picks logged in `sampling.md` MUST match the Bash stdout verbatim. No substitution, no "I picked these and the seed happens to support it," no re-rolling until favorable indices appear.

### The Bash command

For pool size `N`, pick count `K`:

```bash
python3 -c "import random,time,sys; n,k=int(sys.argv[1]),int(sys.argv[2]); s=int(time.time()*1000); print(f'SEED={s}'); print(f'PICKS={sorted(random.Random(s).sample(range(n),k))}')" <N> <K>
```

**Language is not fixed.** `python3` is the reference implementation. Any language works (node, ruby, perl, …) as long as it opens a fresh `int(time*1000)` seed, prints `SEED=<seed>` and `PICKS=<sorted indices>`, and is replayable by an auditor. The capability — a seeded RNG via Bash with verbatim stdout — is the requirement, not the specific binary.

Stdout shape (`N=6`, `K=2`):

```
SEED=1779604358950
PICKS=[1, 4]
```

The model copies both lines verbatim into `sampling.md`. No editing of `PICKS`. If a pick "feels wrong," the only legal response is `resample` or `new options`.

### Audit trail format

Each ms-sample writes a fenced block to `sampling.md`:

````markdown
**ms-sample command:** `python3 -c "..." 10 2`
**stdout:**
```
SEED=1779604461337
PICKS=[2, 7]
```
**resolved picks:** index 2 → *Paolo Girardi*, index 7 → *Karmazid*
````

The Critic re-runs the seed against `N,K` on every audit block; any mismatch fails the run.

### Single-pick variant

For `K=1`, `random.Random(s).sample(range(n), 1)` returns a 1-element list; the model uses the singleton as the pick. No `randint` shortcuts — every sample goes through `random.sample` so the verification command is uniform.

### What still happens in-model

- Generating the candidate pool (enumeration + verbalized reasoning)
- Applying the brief-fitness gate (which surviving subset feeds the Bash call)
- Recording the picks-to-named-items mapping
- Writing `sampling.md`

What does NOT happen in-model: calling `random.Random(...).sample(...)` mentally; "adjusting" picks based on aesthetic judgment; choosing the seed to favor specific indices.

## Constraint VS

Constraints are brief-conditioned, NOT framing-conditioned. Framing-conditioned constraints cluster around obvious moves for that category; brief-conditioned constraints stay grounded in the actual problem.

A valid constraint is a specific, testable rule that applies to the visual output — something a reviewer could check against the finished artifact without interpreting intent. Examples:

- "No cream backgrounds — white or dark only"
- "Type at one size only across the entire piece"
- "No rounded corners anywhere"
- "Maximum two weights from the chosen typeface"
- "No gradients — flat fills only"
- "Imagery only in black and white"

Invalid: vague rules, process notes, or framing guidance ("keep it minimal," "think about the user journey," "stay true to the framing").

Generate 20 candidates, brief-fitness filter to 6–8 strongest, ms-sample 1 (or 2 if the framing is otherwise generic) via the external gate above. The sampled constraint is binding for the build — not softened by the Designer subagent's taste. Tension between constraint and practitioner habit is productive; the Critic notes where the constraint forced a deviation.

## The present + confirm pattern

Every VS step pauses after sampling to present the pool, the seed, the chosen pick, and a brief justification. The user responds with one of:

| Action | Effect |
|---|---|
| `continue` | Accept pick; advance. |
| `resample` | Draw a new ms-clock seed against the SAME pool. |
| `choose N` (or `choose N, M` for K>1) | Manual override to specific index. |
| `new options` | Discard pool; re-brainstorm a fresh pool of the step's specified size; present again. |

Every override is logged with the original sampled pick alongside the final accepted pick. The "picks are non-negotiable mid-loop" rule applies to the **model** (subagents cannot re-roll for taste); only the **human** can override.

## Run modes

Mode sets the confirmation cadence (and, for `lite`, the depth). The audit trail records `mode: <mode>` at the top of `sampling.md`. Canonical definitions live in SKILL.md §Run modes:

- **interactive** (default) — present + confirm every pick.
- **`semi-auto`** (`/inhabited-design semi-auto`) — confirm only the framing and designer picks; seeds, constraint, competitors, and typography fire through.
- **`auto`** (`/inhabited-design auto`) — all VS Steps 2–10 fire through without confirmation.
- **`lite`** (`/inhabited-design lite`) — framing + designer + typography only; skips Steps 6–9 and the critic loop; ICP loop capped at 2 iterations.

A user may interrupt any non-interactive mode and switch to interactive for the remaining steps; document the switch in `sampling.md`.

## Status-write integration

Each VS step marks its `pipeline_status.md` row `in_progress` before beginning, and `done` after the pick is locked. Per `pipeline-status-protocol.md`.

## `sampling.md` audit trail

Top of file: `mode: interactive | auto`, invoked timestamp, brief-ref.

Per VS step: candidate pool table (full enumeration), the Bash ms-sample command, stdout (`SEED=` + `PICKS=`), resolved picks (named items), user action (interactive mode), final accepted pick, brief justification.

Step 12 appends a `## Synthesis` section per `designer-persona-template.md` §Synthesis schema.

### Skeleton

```markdown
# sampling.md — [Project name]

mode: interactive
invoked: 2026-05-23T14:32:11Z
brief-ref: brief.md (v1)

---

## Framing VS

### Candidate pool (≈40 generated to pole quotas)

| idx | pole | framing | brief-fitness note |
|---|---|---|---|
| 0 | scientific | Edward Tufte data-vis small-multiples discipline | ... |
| 1 | spatial | Bawa Sri Lankan tropical-modernist architect | ... |
| ... | ... | ... | ... |

### Bash ms-sample

\`\`\`bash
python3 -c "..." 40 1
\`\`\`

**stdout:**
\`\`\`
SEED=1716474731482
PICKS=[3]
\`\`\`

**resolved pick:** index 3 → cross-cultural pole → Japanese kakejiku hanging-scroll mounting aesthetic
**user action:** continue
**final accepted:** Japanese kakejiku hanging-scroll mounting aesthetic (cross-cultural)

Justification: [one paragraph — why this earns its keep for the brief + ICP]

---

## Designer VS

[same shape: 20-candidate pool (10 disciplines × 2 each), Bash block, resolved + user action + final + justification]

---

## Seeds VS

[same shape: 40-candidate pool (10 artifact categories × 4 each), 2 picks, justification per pick]

---

## Constraint VS

[same shape: 6–8 candidate pool, 1 (or 2) picks, justification]

---

## Competitor VS

→ `competitor-vs-protocol.md` for pool structure
[20-candidate pool + Bash block + 2 picks + per-competitor converge/diverge tables]

---

## Domain research VS

→ `domain-research-vs-protocol.md`
[brief-fitness filtered pool + 3–5 selected refs added to inspiration bank]

### Iteration 2 — additional domain refs
[Bash + new picks + user action — only if iteration feedback opened a direction the bank doesn't cover]

---

## Typography VS

→ `typography-vs-protocol.md`
[15-candidate pool + Bash + locked typeface(s) + banned-canon repool log if triggered]

---

## Synthesis (Step 12)

Composed after Reading all 7 inspiration anchors + claude_anti_defaults.md + this sampling.md from disk.

### Brand personality
- Three concrete words: [...]
  - Derived from: framing #N + designer + ICP register
- Emotional goals: [...]
  - Derived from: [...]
- Tone: [...]
  - Derived from: [...]

### Theme
- Choice: [light / dark]
- Rationale: [...]
- Derived from: framing + ICP + designer

### Aesthetic direction
- Visual register: [...]
- Palette starter: [3–5 hex with selectors and source anchor filenames]
- Typography spirit: [...]
- Anti-references: [...]
- Derived from: framing + seeds + competitors

### Design principles
1. [rule, not aspiration]
2. [...]
3. [...]
- Derived from: ICP + framing + constraint + designer voice
```
