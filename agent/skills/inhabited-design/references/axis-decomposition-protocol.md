# Axis decomposition protocol

How the Designer subagent generates the build output: not as one holistic pass, but as a sequence of per-axis sub-passes, each with **restricted context**.

This protocol was added in May 2026 (v5) after smoke testing v1–v4 showed that even with input-side VS sampling, the output side stayed type-heavy and clustered. Imagery, gradients, illustration, ornament, motion were systematically underspecified — the model defaulted to "type + tabular + hairlines" across briefs.

The root cause: a single Designer subagent pass producing all output fields at once lets the strongest sampled input (usually the framing) pull every output toward itself, collapsing per-axis diversity. T2I literature (Attend-and-Excite, T2I-CompBench, compositional T2I papers) shows that decomposed multi-pass generation with restricted context per pass beats holistic generation on both fidelity and diversity. v5 imports this finding.

## The 10 output axes

Each gets its own generation sub-pass:

| Output axis | Restricted context (sub-pass sees only this) |
|---|---|
| `style_tags` | framing's category only |
| `inspirations` | all 7 inspiration-bank anchors (this axis is the cross-anchor summary) |
| `color_palette` | framing + seeds + sampled constraint |
| `typography` | record from Typography VS step (no new generation — just transcribe) |
| `key_visual_elements` | framing + seeds + competitors |
| `mood` | framing's emotional register only (do not see designer / seeds / typography) |
| `imagery` | framing + seeds + designer + constraint — photography/illustration direction + hero treatment |
| `surface_treatment` | framing + constraint + designer voice — gradients/textures/patterns/materials |
| `ornament` | framing + designer + seeds — decorative motifs, drop caps, marginalia, glyphs |
| `motion` | framing + constraint — kinetic register, transitions, scroll behavior |

The restricted-context principle: when generating axis X, the Designer subagent does NOT see the sampled inputs that aren't supposed to condition X. Hide them in the sub-prompt. This is what prevents axis bleed.

## Procedure

For each axis above (in any order):

1. **Construct the sub-prompt.** Include only:
   - The brief (App X + ICP)
   - The output axis being generated, including the field's length cap from the brief schema
   - The restricted-context inputs from `sampling.md` listed for that axis
   - The instruction: "Generate ONLY this output field. Do not reference inputs outside the restricted context for this axis."

2. **Run the generation.** Produce the field's value (e.g., 4-6 color entries for `color_palette`, 3-5 imagery items, etc.).

3. **Write the attribute-binding manifest entry.** For each output element, name the specific sampled axes it derived from. Save to `borrowings_v{cycle}.md` (see `borrowing-summary-protocol.md`).

4. **Repeat** for the remaining 9 axes.

5. **Assemble.** Combine the per-axis outputs into the final JSON in the brief's schema order.

## Worked example — `imagery` sub-pass

Inputs visible to this sub-pass:
- Brief: "Design a booking page for a remote luxury treehouse resort..."
- Framing (from sampling.md): "Hiroshi Sugimoto large-format long-exposure stillness as composition logic"
- Sampled seeds: ["Edward Steichen Family of Man catalog spread", "Sugimoto Seascapes monograph plate"]
- Sampled designer: "Veronika Burian (type design)"
- Sampled constraint: "no cabin/interior photography on first paint"

Inputs HIDDEN from this sub-pass:
- Competitors (don't condition imagery)
- Typography picks (don't condition imagery)
- Domain research (don't condition imagery)
- Mood, color_palette, key_visual_elements (other axes — produced separately)

Generated output for `imagery`:
```json
"imagery": [
  "long-exposure cloud-forest plates, no people",
  "monograph-scale hero with edition number caption",
  "horizon-line anchored composition across all panels",
  "plate-format aspect 1.4:1, not 16:9 wide"
]
```

Attribute-binding manifest entry:
```
imagery[0] = "long-exposure cloud-forest plates, no people"
  derived from: framing "Sugimoto stillness as composition logic"
              + seed "Sugimoto Seascapes monograph plate"
              + constraint "no cabin/interior on first paint"

imagery[1] = "monograph-scale hero with edition number caption"
  derived from: framing's photographic-monograph register
              + seed "Steichen Family of Man catalog spread"
```

## Why restricted context matters

If the imagery sub-pass also saw the sampled typography (e.g., "Tiempos Text + Söhne Mono"), the model might generate imagery that "matches the type" — leading to imagery that's secretly just typographic in flavor. The literal hiding of non-relevant inputs forces the imagery axis to commit to a real photographic/illustration decision rather than averaging into the type aesthetic.

This applies even more strongly to the new axes (imagery, surface_treatment, ornament, motion). Without restricted context, these would get absorbed into "key_visual_elements" or "mood." With restricted context, they get their own decision space.

## Axis priority and dependencies

Most axes are independent and can run in any order. A few dependency rules:

- `inspirations` runs LAST because it summarizes across all the anchors (which are all sampled by then)
- `typography` is recorded from the Typography VS step — no new generation needed
- All other axes (`color_palette`, `mood`, `imagery`, `surface_treatment`, `ornament`, `motion`, `style_tags`, `key_visual_elements`) can run in parallel or any order

## What this is not

- **Not a brief-fitness gate per axis.** The brief fitness has already been applied at each VS sampling step. Per-axis generation here is about restricted-context conditioning, not gatekeeping.
- **Not a per-axis VS sample.** No ms-sampling at the output step. The Designer just generates the field value conditioned on the restricted-context inputs.
- **Not a quality check.** The critic (see `adversarial-critic-protocol.md` factor 4: `fits axis manifestation`) verifies coherence after the fact.

## Relationship to other protocols

- `borrowing-summary-protocol.md` — defines the attribute-binding manifest format that each sub-pass writes to
- `adversarial-critic-protocol.md` — defines factor 4 (`fits axis manifestation`) that scores whether each output axis actually reflects its restricted-context inputs
- `designer-persona-template.md` — defines how the Designer persona is built; the per-axis decomposition is the *output protocol* the persona follows during build

The 6 brief-schema output fields plus the 4 v5 visual-vocabulary additions (10 total) are the axes this protocol decomposes. The decomposition is the v5 mechanism for breaking the "type-heavy + tabular" attractor that survived v4.
