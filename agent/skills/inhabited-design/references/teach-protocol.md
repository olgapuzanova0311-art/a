# Teach Protocol

A one-time per-project setup that captures the **stable** design context (App X, ICP, accessibility) into `inhabited.md` in `.inhabited/`. The scoring rubric is fixed at the default 7 factors and is not part of the per-project context. Aesthetic and brand decisions — voice, theme, references, design principles — are synthesized downstream from the sampled framing, designer, seeds, and competitors, and live in `claude_designer.md` (written in Step 12). Capturing them here biases the VS process.

## When to run

Run **once per project**, before the first sampling step. Subsequent invocations on the same project skip the teach flow and proceed directly to sampling.

Re-run only when:
- The user explicitly asks (`/inhabited-design teach` or "update the design context")
- `inhabited.md` is missing a required section (older format / partial fill)
- The user's request implies a change to the stable context ("we're pivoting from runners to cyclists" — re-run, don't paper over)

## Source priority

1. **`inhabited.md` in `.inhabited/`** — authoritative if present and complete
2. **README.md, CLAUDE.md, package.json** — for project name, tech stack, stated purpose, target audience if documented
3. **AskUserQuestion** — only for gaps the codebase can't fill

**Never infer the ICP from the codebase.** Code tells you what was built, not who it's for. Ask.

## What `inhabited.md` must contain

```markdown
# Inhabited design context — {{App X name}}

> Stable per-project context. Sampling is fresh per session; this file is not.

## App X
- **Purpose** (one sentence): {{e.g., "A weekly menu planner that turns Sunday from chore to ritual."}}
- **The single most important user moment**: {{e.g., "Sunday 4pm, deciding what to cook, glass of wine."}}
- **Out-of-scope guardrails**: {{what NOT to build}}

## ICP
- **Identity**: {{specific named-feeling individual — e.g., "Mara, schoolteacher in Eau Claire, 38"}}
- **Context**: {{where / when / why they use this}}
- **Emotional state at moment of use**: {{e.g., "tired but contented, wants ritual not task"}}
- **What success looks like for them**: {{not for the business — concrete user outcome}}

## Accessibility
- **WCAG level**: {{e.g., "AA"}}
- **Specific user needs**: {{e.g., "user has reading glasses; default body 18px"}}
- **Reduced motion / color blindness**: {{considerations}}

## Scoring rubric

Fixed at the 7 defaults (Usability, Flare, Personality, Visual Design, Originality, Visual Impressiveness, Wow Factor). Do not record per-project modifications.

## Notes

{{Anything else the user wants persisted across sessions.}}

---

Last updated: {{YYYY-MM-DD}}
```

## Procedure

1. **Initialize the working directory + pipeline status.** Create the `.inhabited/` directory at the project root if it doesn't exist — every file the skill generates lives there. If `.inhabited/pipeline_status.md` does not exist, create it with all 14 steps at `pending` per `pipeline-status-protocol.md`. Then `Edit` Step 1's row to `in_progress` before beginning work.

2. **Read existing project files in parallel** — `inhabited.md`, `README.md`, `CLAUDE.md`, `package.json`; `Glob` for `brand.*`, `design-system.*`, `tokens.*`. If `inhabited.md` exists and has every required section filled (no `{{...}}` left), skip to Step 6 — mark Step 1 `done` and proceed to sampling.

3. **AskUserQuestion for gaps only.** Batch in groups of ≤4 with clear options. Required questions only if the codebase hasn't already answered:
   - App X purpose (one sentence)
   - The single most important user moment (when / where / emotion)
   - ICP — specific named-feeling individual (not "users")
   - Out-of-scope guardrails (what NOT to build)

   Do NOT ask about aesthetic or brand decisions — voice, references, theme (light/dark), design principles. Those are synthesized downstream after sampling. The scoring rubric is fixed; do not ask about it.

4. **Write `inhabited.md`** synthesizing all sources into the template above. No `{{...}}` placeholders may remain.

5. **Offer to append a ≤150-word Design Context summary to `CLAUDE.md`** via `AskUserQuestion` so other Claude sessions see it. Append (or update in-place) only if the user agrees.

6. **Mark Step 1 done.** `Edit` `pipeline_status.md` row 1: `status` → `done`, `Completed` → ISO 8601 timestamp, `Artifact` → `inhabited.md`. Update `Last updated`. Return a one-paragraph summary of the captured context and proceed to Step 2 (Framings VS).

## Common pitfalls

| Pitfall | Fix |
|---|---|
| Teach flow re-asks every question even though `inhabited.md` exists | Step 2 must short-circuit if the file is complete; check first. |
| Teach flow infers ICP from codebase ("looking at this app, the users are…") | Never. Always ask. Code says what was built, not who for. |
| Teach flow asks about aesthetic or brand decisions (voice, references, theme, principles) | These are downstream of sampling. Asking up-front narrows the framing pool and biases the VS process. |
| `inhabited.md` written with `{{...}}` placeholders left in | Every placeholder is a gap the user should have answered. Re-ask. |
| User runs teach to update but it asks every question again | Read existing file first; only ask about the section the user wants to change. |
