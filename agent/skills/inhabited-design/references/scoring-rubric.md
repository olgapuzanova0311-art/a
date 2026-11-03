# Scoring Rubric

The 7 fixed factors. They apply unmodified to every project.

## Default 7 factors

| Factor | Definition | What 10/10 looks like |
|---|---|---|
| **Usability** | Can the target user accomplish their goal smoothly, with no friction? | Every action is obvious, intentional, and reachable. Empty states guide. Errors recover. Mobile and edge cases covered. |
| **Flare** | Does it have signature small touches that are NOT in the spec? | Earned moments of personality — a single piece of motion, a copy line, a typographic detail — without trying for a parade. |
| **Personality** | Does it have a clear, consistent voice? | The product reads as someone made it. Empty states, error messages, and microcopy share a register. |
| **Visual Design** | Is the craft tight on type, color, spacing, motion? | Type scale obeyed. Palette small and intentional. Spacing on-system. Motion timed and eased. |
| **Originality** | Does it feel fresh, not derivative? | A move not present in the obvious-reference apps in the category. Synthesis-not-copy. |
| **Visual Impressiveness** | Does it catch the eye? Carries weight at first glance? | A composition where something specifically rewards a second look — a chart form, a typographic moment, a layout choice. |
| **Wow Factor** | Is there a moment that stops you? | Some specific interaction or reveal that feels like a gift. Earned, not gimmicky. |

## The rubric is fixed

The 7 factors above are the rubric for every project. **Do not add, remove, rename, reweight, or otherwise modify them.** Do not propose modifications to the user, and do not accept user-initiated modifications mid-conversation — if asked, explain that the rubric is fixed by design and proceed with the default 7.

Why: factor modifications were a major source of attractor drift in earlier versions. Renaming "Wow Factor" to something tamer ("Status Coding", "Sunday Feeling", "Restraint Discipline") let the design quietly skip the moment that's supposed to make the build memorable. Adding domain-specific factors ("Accessibility", "Trust", "Clarity") shifted scoring weight away from the rubric's actual job, which is to push the build against attractors that the brief alone won't push it against. The 7 factors stay; brief-specific concerns belong in App X, the constraint, and the design principles — not in the rubric.

## Scoring discipline (for the ICP persona)

The ICP must:
- Score honestly — neither charitable nor jaded
- Give 10/10 if genuinely earned
- Withhold 10/10 if not earned, AND say what would push it there
- Be specific in "what's missing" — pointable, not vibes

The ICP persona file (see `icp-persona-template.md`) encodes this discipline.

## The runner_feedback.md scoring section format

For automated parsing, the feedback document must include a **Scores** section with this exact structure:

```markdown
## Scores
- Usability: X/10 — [what's missing or why it's 10]
- Flare: X/10 — [what's missing or why it's 10]
- Personality: X/10 — [what's missing or why it's 10]
- Visual Design: X/10 — [what's missing or why it's 10]
- Originality: X/10 — [what's missing or why it's 10]
- Visual Impressiveness: X/10 — [what's missing or why it's 10]
- Wow Factor: X/10 — [what's missing or why it's 10]
```

The parsing logic in `iteration-loop.md` looks for `- {factor name}: {N}/10` lines using these exact 7 factor names.

## Stop condition

Loop exits when **all 7 factors hit 10/10**.

## Stuck-factor escape

If a single factor stays at the same score for **3 consecutive iterations**, do not drop it from the rubric. The rubric is fixed. Instead, surface what specifically isn't landing for that factor and target it with the next iteration's design move (a new component shape, a new visualization, a new layout principle) rather than re-polishing. Stuck factors are usually gated on a structural decision, not on rubric definition.

## Empirical observations from the experiment

- **Personality** typically reaches 10 first (within 1–2 iterations). It's baked into every line of code from the persona's voice.
- **Usability + Visual Design + Personality** often hit 10 by iteration 3. Craft fundamentals are reproducible.
- **Originality** often requires a structural move (introduce a new component shape, a new visualization, a new layout principle) — can't be polished in.
- **Visual Impressiveness + Wow Factor** are the stickiest. Typically gated by a single specific design choice (an animation that doesn't reach, a moment that doesn't land). The fix is usually one targeted change, not a redesign.
