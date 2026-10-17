# Pipeline Status Protocol

A discipline for tracking 14-step pipeline progress in `pipeline_status.md` in `.inhabited/`, enabling resume across sessions, user vetoes, or context loss.

## File format

`pipeline_status.md` lives in `.inhabited/` alongside `inhabited.md` and `sampling.md`:

```markdown
# Pipeline Status

Created: {{ISO 8601 timestamp at first write}}
Last updated: {{ISO 8601 timestamp at each subsequent write}}

## Steps

| # | Step | Status | Completed | Artifact |
|---|---|---|---|---|
| 1 | Teach gate | done | 2026-06-06T14:20:00Z | inhabited.md |
| 2 | Framings VS | done | 2026-06-06T14:23:00Z | sampling.md §Framing |
| 3 | Brief-fitness gate | done | 2026-06-06T14:23:00Z | sampling.md §Framing (≈40 pole-quota pool) |
| 4 | ms-sample framing | done | 2026-06-06T14:24:00Z | sampling.md §Framing (locked pick) |
| 5 | Designer VS | in_progress | — | (presenting candidates) |
| 6 | Seeds VS | pending | — | — |
| 7 | Constraint VS | pending | — | — |
| 8 | Competitors VS | pending | — | — |
| 9 | Domain research VS | pending | — | — |
| 10 | Typography VS | pending | — | — |
| 11 | Anti-defaults research | pending | — | — |
| 12 | Designer persona + per-axis output | pending | — | — |
| 13 | Critic loop | pending | — | — |
| 14 | ICP loop | pending | — | — |

## Resume notes

{{Free-form context for resuming — e.g., "user vetoed seed pick at 14:25; re-rolling with adjusted candidates."}}
```

## Status values

| Value | Meaning |
|---|---|
| `pending` | Not yet started. Initial state for every step on a fresh run. |
| `in_progress` | Step started but not finished. Set before work begins so a crash leaves a recoverable trace. On resume, treat as `pending` (restart from scratch — do not trust partial work). |
| `done` | Step's completion criterion met per the table below. Artifact exists and was verified. |
| `failed` | Step ran but couldn't complete (e.g., brief-fitness gate failed 3+ times, WebSearch unavailable, user explicitly stopped). Resume notes capture the reason. |

## Per-step completion criteria

A step is `done` only when its named artifact exists and matches its spec. Marking `done` prematurely poisons the resume — downstream steps trust the marker.

| # | Step | Completion criterion |
|---|---|---|
| 1 | Teach gate | `inhabited.md` exists with every required section filled (no `{{...}}` placeholders) per `teach-protocol.md` |
| 2 | Framings VS | `sampling.md` §Framing contains the ≈40 generated pole-quota pool (pole-tagged) with brief-fitness reasoning per candidate |
| 3 | Brief-fitness gate | `sampling.md` §Framing contains the ≈40 generated pool with quota self-check verified (≤2/40 scientific/instrument) |
| 4 | ms-sample framing | `sampling.md` §Framing contains the locked pick with `SEED=...` + `PICKS=...` Bash stdout matching the logged pick verbatim |
| 5 | Designer VS | `sampling.md` §Designer contains the 20-candidate enumerated pool + locked pick + ms-seed |
| 6 | Seeds VS | `sampling.md` §Seeds contains the 40-candidate pool + 2 locked picks + ms-seed |
| 7 | Constraint VS | `sampling.md` §Constraint contains the 6–8 candidate pool + 1 (or 2) locked pick(s) + ms-seed |
| 8 | Competitors VS | `sampling.md` §Competitors contains the pool + 2 locked picks + per-competitor converge/diverge tables |
| 9 | Domain research VS | 3–5 domain references added to the inspiration bank with brief-fitness reasoning logged |
| 10 | Typography VS | `sampling.md` §Typography contains the candidate pool with brand-voice + physical-object anchors + locked typeface pick |
| 11 | Anti-defaults research | `claude_anti_defaults.md` exists with 8–15 research-derived patterns (not copied from prior project) |
| 12 | Designer persona + per-axis output | `claude_designer.md`, `claude_icp.md`, `claude_critic.md` all exist; `borrowings_v1.md` contains the attribute-binding manifest for all 10 axes |
| 13 | Critic loop | `v1_critic/critic_verdict_{cycle}.md` exists with all 4 factors at 10/10 + constraint honored + slop gate PASS + state-coverage gate PASS |
| 14 | ICP loop | `iter_{N}/runner_feedback.md` exists with all 7 factors at max, reviewed on real images (filled each iteration) |

## Discipline

**Read-on-startup.** Before Step 1, `Read` `pipeline_status.md` if it exists in `.inhabited/`. Find the first step whose status is not `done` — resume from there, NOT from Step 1. Before resuming, re-read all artifacts produced by prior `done` steps: minimum re-read set is `inhabited.md`, `sampling.md`, any persona files (`claude_designer.md`, `claude_icp.md`, `claude_critic.md`), `claude_anti_defaults.md`, and any borrowings file. Conversation context is lost across sessions; the files are the state.

If the file does not exist, initialize it with all 14 steps at `pending` using the template at the top of this file, then proceed to Step 1.

**Mark-in-progress before work.** Before starting a step's work, `Edit` the row: `status` → `in_progress`. Update the `Last updated` line. Then begin. The `in_progress` marker is the recovery anchor — a crash or context exhaustion leaves a clear signal that this step started but didn't finish.

**Write-on-completion.** At the end of each step, `Edit` the row: `status` → `done`, `Completed` → ISO 8601 timestamp (use `date -u +"%Y-%m-%dT%H:%M:%SZ"` if uncertain), `Artifact` → path or section reference. Update `Last updated`. Use `Edit`, not `Write` — preserves prior rows verbatim.

**Mark-failed on hard failure.** If a step cannot complete (e.g., brief-fitness gate fails 3+ times, WebSearch unavailable for Step 11, user explicitly stops the run), `Edit` the row to `failed` and add a brief failure note to `## Resume notes` (timestamp + one-line reason). Surface the failure to the user; do not silently proceed.

## Resume rules

- Resume from the first non-`done` step.
- Steps with `in_progress` or `failed` are restarted from scratch — their partial outputs are not trusted.
- The `Resume notes` section is the place for human-readable handoff context — what was happening, why a step is `in_progress` or `failed`, anything the next session needs to know.
- The user may manually edit `pipeline_status.md` to force a step back to `pending` (e.g., "I want to re-roll the framing") — respect the edit.

## Forbidden

- **Do not skip steps based on the status file alone.** If Step 4 is `done` but `sampling.md` is missing the locked framing pick, the status is lying and the step must be re-run. Artifacts are authoritative; the status file is a fast index.
- **Do not mark `done` without verifying the artifact** matches the completion criterion in the table above.
- **Do not edit prior completed rows** except to correct a misrecorded status.
- **Do not skip the `in_progress` marker** to save a write. The marker is the only signal a crash leaves behind.
