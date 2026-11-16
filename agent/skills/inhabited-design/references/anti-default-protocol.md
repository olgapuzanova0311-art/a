# Anti-Default Protocol

Generates a project-specific list of **current** AI-design tells via web research. Output: `claude_anti_defaults.md` next to the Designer persona. Re-read during each major design decision alongside the inspiration bank.

## Why research, not hardcode

What reads as "AI-generated design" shifts faster than any skill file can track. A list baked into this skill in mid-2026 would call out Space Grotesk, purple-on-white gradients, and bento grids; six months later the failure mode is *different* fonts, *different* gradients, *different* grids. The point isn't to memorize anti-patterns — it's to **find out** what the current ones are, every time the loop runs.

## When this happens

**Step 1 of the inspiration-bank protocol**, before visiting any reference site. The Designer cannot write design code until both `claude_anti_defaults.md` AND the inspiration bank are populated.

## Search strategy

Run **3–6 web-search queries** (via `WebSearch`, Brave Search, or any web-search tool — see SKILL.md §Requirements & preflight), mixing generic AI-design tells with domain-specific tropes. If no web-search tool is available, mark Step 11 `failed` per `pipeline-status-protocol.md` and surface it; do not fabricate tells.

**Generic queries (pick 2–3):**
- "signs of AI generated web design {{current year}}"
- "AI design tells UI"
- "how to spot AI generated UI"
- "AI slop design patterns"
- "overused fonts in AI generated design"
- "overused color schemes AI design"

**Domain-specific queries (pick 1–3):**
- "{{domain}} design clichés"
- "AI generated {{domain}} design"
- "overused {{domain}} UI patterns"
- "generic {{domain}} app design tropes"

For each query, read the top 3–5 results. Skim for **concrete** patterns — not generalities like "lacks personality" but specific tells like "centered hero with subtle gradient background and 600-weight headline" or "bento grid of feature cards with rounded-2xl corners."

## What to extract

For each pattern surfaced by **≥2 sources** OR named by a **credible single source** (designer post on X/Bluesky, Awwwards critique, design publication, Codrops/Smashing piece), capture:

1. **The pattern** — concrete enough to recognize in a screenshot (font name, color scheme, layout move, motion cliché, copy trope)
2. **Why it reads as AI** — one line on the failure mode
3. **The alternative** — a direction, not a prescription

Skip patterns that are:
- Too abstract to act on ("lacks soul," "feels generic")
- Already covered by the domain anti-patterns in the persona file
- Older than ~12 months unless still cited as a current failure mode

**Target: 8–15 entries.** Fewer = under-researched. More = unfocused and the Designer stops referring to the file.

## Output format

Save to `claude_anti_defaults.md` next to `claude_designer.md`:

```markdown
# Anti-Defaults: Current AI-Design Tells

Generated from web research on {{YYYY-MM-DD}}. Re-research if this file is older than 6 months or the project shifts domain.

## Sources consulted

- {{URL}} — {{short note on what it surfaced}}
- {{URL}} — ...

## Patterns to avoid

### {{Pattern name}}
**Tell:** {{concrete description}}
**Why it reads as AI:** {{one line}}
**Instead:** {{direction, not prescription}}

### {{Next pattern}}
...
```

## How the Designer consults this file

Same discipline as the inspiration bank:
- Read at the start of design work (Read tool on the file)
- Re-read before each major design decision (typography, color, layout, hero composition, motion)
- After producing a design move, check: does any entry in this file match? If yes, revise *before* the build reaches the ICP.

## When WebSearch is unavailable

**Hard fail.** Ask the user for 3–5 concrete current AI-design tells they've noticed, then synthesize those into the same output format. **Do not fall back on the Designer's own knowledge** — that knowledge is exactly what the model converges on, and is the failure mode this protocol exists to interrupt.

## Lifecycle

- One file per project, generated fresh during persona generation
- Date the file at the top
- Re-research if the project's build extends beyond 6 months
- **Do not copy `claude_anti_defaults.md` from one project to another.** The research must run again — what reads as AI in May won't match what reads as AI in November

## Common failures

| Failure | Fix |
|---|---|
| Anti-list is generic ("be original," "avoid clichés") | Each entry must be a specific recognizable pattern. Reject anything you couldn't point at in a screenshot. |
| Designer skips the lookback | The persona file enforces re-reading as a hard rule. If skipped, treat as a violation of the inspiration-bank discipline. |
| List grew to 30+ items | Trim to 8–15. Beyond that, the Designer can't hold them and starts ignoring the file. |
| Research surfaced only one source per pattern, all from the same publication | Mix sources: designer X/Bluesky posts, Awwwards critiques, Reddit r/web_design, Codrops, Smashing, indie blogs. Single-outlet research narrows the lens. |
| Anti-list duplicates the domain anti-patterns already in the persona | Keep them distinct. Persona = what designers in this domain get wrong. Anti-defaults = what AI models converge on regardless of domain. |
