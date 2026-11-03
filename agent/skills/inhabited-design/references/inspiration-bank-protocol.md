# Inspiration bank protocol

The discipline that converts "look around for inspiration" into actual saved files the agent re-opens during the build. This version of the protocol replaces the parent's 5-7 composition with the new locked 7-anchor structure for the VS variant.

---

## 7-anchor composition

The inspiration bank at v1 has exactly 7 anchors, locked:

| Slot | Count | Source |
|---|---|---|
| Framing-seeds | 2 | `sampling-protocol.md` §Seeds VS (framing-conditioned) |
| Designer signature work | 1 | `sampling-protocol.md` §Designer VS — the canonical representative work of the sampled designer |
| Brief-domain competitors | 2 | `competitor-vs-protocol.md` (with per-element converge/diverge tables in borrowing summary) |
| Brief-domain domain research | 2 | `domain-research-vs-protocol.md` |
| **Total at v1** | **7 anchors** | **Locked** |

Each anchor traces back to a millisecond-clock RNG seed plus a VS candidate enumeration. The audit trail (`sampling.md`) makes every anchor reproducible.

**Hard rules for the 7-anchor set:**

- **Framing-seeds (2).** Both seeds come from the framing-conditioned VS draw in `sampling-protocol.md` §Seeds VS. They are non-negotiable once drawn — even an off-genre seed stays in. The off-genre-ness is the point. Each seed contributes exactly 1 representative image (see Single clean image section below).

- **Designer signature work (1).** The representative artifact people in the field point to first for the sampled designer, calibrated to the brief (e.g., Rams → Braun T1000 for a product brief; Tadao Ando → Church of the Light for an architecture-adjacent brief). The Designer defends the choice.

- **Brief-domain competitors (2).** Both competitor anchors come from the `competitor-vs-protocol.md` VS draw. Each must have per-element converge/diverge tables in the borrowing summary — not just "we looked at it" but specific elements and explicit converge/diverge decisions for each.

- **2 brief-domain domain research** anchors come from the `domain-research-vs-protocol.md` VS draw. Each must contribute at least one named visual element to the build.

- **Positive borrowings only (HARD GATE).** Every anchor must contribute at least one named, specific visual element to the build (typeface, hex color, glyph, layout pattern, composition move). Cautionary references — "we refused this attractor" / "borrowing the negative example" — do NOT belong in the bank; they live in `claude_anti_defaults.md`. If a domain reference can only be described as "what NOT to do," it is an anti-default, not an inspiration.

- **Anti-pattern to watch:** domain additions that neutralize the seeds' off-genre energy. If seed 1 is "Tadanori Yokoo psychedelic poster" and domain refs are all clean SaaS dashboards, the poster's contribution collapses. Force domain additions to resonate WITH the seeds' poles, not pull back to the model's default. The adversarial critic catches this collapse via the "Fits sampled inputs" score.

---

## Iteration extensions

The v1 bank is 7 anchors, but the Designer may extend during iteration via the rule in `domain-research-vs-protocol.md` §Iteration re-sample rule.

**Summary of extension rules:**

- The Designer may VS-sample **+2 additional domain research references per iteration**.
- **Cap: +6 total additional anchors across all iterations** (3 iterations × 2 each, or any distribution up to +6).
- Originals stay — no swapping. Extensions add to the bank; they do not replace existing anchors.
- Each addition gets its own millisecond-clock RNG seed recorded in the audit trail (`sampling.md`).
- Every addition goes through **present + confirm with the user** before it enters the bank.
- Final bank can grow from **7 → 13 anchors maximum** (7 locked + 6 extended).

Extensions follow the same positive-borrowings gate: each added anchor must contribute a named visual element, and the Designer writes its borrowing line before moving on.

---

## Each reference is a single clean image of the work

A reference is not a URL — it is an image you can put on your wall.

**Grids fail this gate. Moodboards fail this gate. Contact sheets fail this gate.**

- Search-results grids are illegible to the AI looking at them — a 4×4 grid of small thumbnails is a placeholder, not a source.
- Pinterest board screenshots fail this gate.
- Moodboard collages fail this gate.
- Contact sheets of small thumbnails fail this gate.

Each anchor reference must be downloaded as a **single canonical image of the named work**. The work must occupy ≥40% of the frame at 1600px. If it does not, the reference fails this gate.

**Use the Read tool on the saved file, not on URLs.** URLs alone don't count. A reference is only in the bank once its image file is saved locally and opened with the Read tool at least once to confirm legibility.

**Two acceptable capture methods:**

- **Direct download** (preferred — avoids contention with parallel agents):
  ```bash
  curl -L -o references/01_source_work.png 'https://example.com/path/to/image.png'
  ```
- **Playwright screenshot** (fallback for pages where the design lives entirely in CSS):
  ```
  browser_navigate → http://example.com
  browser_take_screenshot → references/02_designsystem_chrome.png
  ```

**Naming convention:** `NN_<source>_<what>.png` where `NN` is the two-digit entry order matching `inspiration.md`.

**Unacceptable file names:** anything containing `_search`, `_grid`, `_moodboard`, `_pinterest`, or `_collage`. These naming patterns signal a gate failure.

---

## Re-opening discipline

**Once the bank is built, you keep going back to it.** The references are not a one-time intake — they are the source you return to throughout the build.

Before each major design decision (typography choice, color picking, layout move, motion timing, empty-state composition, spacing system):

1. Open the relevant reference image **from the file, not from memory** (Read tool on the saved image).
2. Look.
3. Then continue.

The discipline is: **build → look → adjust → continue**, not **build straight through and hope memory holds**.

The bank is load-bearing, not decorative. If a component was designed without re-opening its anchor reference, that is drift; back up and look before continuing.

**Component-to-anchor mapping:** at bank-assembly time, the Designer notes which anchor is responsible for which design decision zones (e.g., "seed 1 → grid system and type scale; competitor 1 → color palette; designer ref → empty state treatment"). Re-opening is intentional, not random.

If a component went down without revisiting its anchor reference, that is drift. Back up and look.

---

## Per-iteration image fill

Photography is filled **at the end of each design iteration**, before that iteration's ICP review — not in a single post-loop pass. The ICP therefore always reviews real images, so an image that breaks the composition is caught the iteration it lands, not at the very end. The trade-off is re-sourcing when a slot's design changes; the benefit is that the ICP's 7-factor review covers the real artifact every pass.

**Source is stock only: Unsplash and Pexels.** No AI image generation. No other providers.

**Step 1: Reserve image slots while building the iteration**

When the design needs photography, capture image intent in `inspiration.md`, not the image itself:

- **Where** in the layout
- **Aspect ratio and approximate size**
- **Subject and mood** — concrete (e.g., "warm dawn light, anonymous runner mid-stride, midwestern field"), not generic ("running photo")
- **Tone/treatment** — saturated vs. muted, warm vs. cool, full-color vs. duotone

In the build, reserve each slot with a placeholder that:

- Holds the correct dimensions and aspect ratio so layout doesn't reflow when the real image lands
- Is visibly distinct from final state (flat tone or hatched fill, not pretending to be the photo)
- Embeds the intent as an `IMAGE_INTENT` comment so the end-of-iteration fill step can find and fill it

Example marker:

```html
<!-- IMAGE_INTENT: hero / 16:9 / warm dawn light, anonymous runner mid-stride, midwestern field / saturated warm -->
<div class="reserved-image" data-image-intent="hero / 16:9 / warm dawn light..."></div>
```

**Step 2: Fill every placeholder at the end of the iteration**

Before the pixel gate / ICP handoff, walk the build, find every `IMAGE_INTENT` placeholder, and fill each from stock. This applies to the v1 build before the first ICP review and to every subsequent iteration's revision. For each placeholder:

1. **Read the intent** (where, aspect, subject, mood, treatment) from the marker.
2. **Re-open the 2–3 anchor references most relevant to this slot** — `Read` from disk, not from memory. This conditions the search query and the pick discipline.
3. **Compose the search brief in-context** from the sampled designer, the palette (hex values from `borrowings_v{N}.md`), the surface/mood register, and the anti-references (`claude_anti_defaults.md`). The `IMAGE_INTENT` string is intentionally thin; the search brief is the craft moment.
4. **Search Unsplash, then Pexels** (stock only — no AI generation, no other providers). Apply the gates:
   - **Original?** Not the overdone stock photo / obvious first result.
   - **Appropriate?** Does it serve the brief and the ICP's reality? (e.g., for first-time marathoners, no chiseled elites.)
   - **Never the first result.**
5. **Download** to `references/photos/` named `NN_<source>_<slot>.jpg`, where `<source>` is `unsplash` or `pexels`.
6. **Downscale** to ≤1600px on the longest edge (see Image file size guard below); **format gate** png/jpg/jpeg/webp/gif only — never SVG/AVIF.
7. **Place** the image — match the reserved aspect ratio (crop to fit, do not stretch).
8. **Record provenance in `inspiration.md`** — one line per filled slot: slot name, source (unsplash/pexels), URL, one-line rationale.

**Step 3: Re-source only on change**

Carry filled images forward between iterations. When a later iteration changes a slot's layout, palette, or intent, re-run Step 2 for that slot only; unchanged slots keep their image (don't re-source needlessly). The ICP reviews each iteration with real images in place — if a chosen image breaks the design, the ICP flags it and the Designer re-sources (different image, same intent) in the next pass, the same loop that handles every other ICP finding. There is no separate post-loop fill phase and no separate post-fill review.

---

## Palette borrowing gate

The build's color scheme must be borrowed from at least one anchor reference as a **full palette of ≥3 named colors beyond pure neutrals**. White, black, and grey do not count toward the three.

**Gate requirements:**

- The Designer names the palette-source reference (e.g., "Competitor 1: Strava's activity card").
- The Designer lists the hex values borrowed, with corresponding CSS custom property names and selectors, in the borrowing summary.
- The palette derivation is traceable: the borrowed palette must be visible in the anchor image and the hex values must match or closely derive from what appears in that image.

**The "monochrome + one accent" pattern is treated as drift toward the cream-paper-serif attractor.** It is the model's default gravity well — high-contrast type, warm neutral backgrounds, single accent color. This pattern is not prohibited, but it requires explicit justification naming the anchor reference that motivated it. Lean toward more color.

**Palette gate in practice:**

- If the anchor images contain only neutrals, the Designer must note this explicitly and apply the iteration extension to find a more chromatic anchor before closing the loop.
- The palette borrowing entry in `borrowing-summary-protocol.md` must name the reference, list ≥3 hex values, and map each to a CSS selector.

---

## Image file size guard

All downloaded reference images must be downscaled to **≤1600px on the longest edge** after download. This avoids the Read tool's 2000px dimension limit.

For full rules and implementation commands, see `file-size-guards.md`.

**Quick implementation:**

```bash
python3 -c "from PIL import Image; img=Image.open('references/01_x.png'); img.thumbnail((1600,1600)); img.save('references/01_x.png')"
```

**Format gate:** Save only **PNG, JPG, JPEG, GIF, or WebP** formats. Never SVG or AVIF — the Read tool cannot display them. If a downloaded file is SVG or AVIF, discard it and find an alternative source or take a Playwright screenshot.

This guard applies to both anchor references and post-design photography. Every image in `references/` must pass the format gate and the size gate before use.

---

## Verification gates

The following gates collectively enforce this protocol. Failure of any gate is a build block.

**Inspiration-bank gate (enforced in SKILL.md)**

- All 7 anchors exist as saved image files in `references/`.
- Each is a single clean image (not a grid, moodboard, or contact sheet).
- Each is re-opened (Read tool on the file, not on a URL) at least once during the major design decisions it is responsible for.
- Each has a borrowing line in `inspiration.md` naming at least one specific visual element contributed.

**Critic's `fits sampled inputs` factor (`adversarial-critic-protocol.md`)**

- Traceable contribution from each of the 2 framing-seeds is present in the design — not just acknowledged, but visible.
- The designer-ref contribution is present and named.
- The adversarial critic scores this factor; a low score indicates seed energy was neutralized by domain additions.

**Critic's `fits competitor judgment` factor (`adversarial-critic-protocol.md`)**

- Per-element converge/diverge tables exist for both competitor anchors in the borrowing summary.
- Each table names specific visual elements and records the converge/diverge decision with rationale.
- Missing tables = gate failure.

**Borrowing summary gate (`borrowing-summary-protocol.md`)**

- Per-reference named-element log covers all 7 (or extended) anchors.
- Each entry specifies the element borrowed (not just "inspired by"), the CSS selector or component where it appears, and the iteration in which it was applied.

**Palette borrowing gate**

- ≥3 named colors beyond pure neutrals are borrowed from at least one anchor reference.
- Hex values, custom property names, and selectors are logged in the borrowing summary.
- The palette-source reference is named.

**Per-iteration image-fill gate**

- Every `IMAGE_INTENT` placeholder is filled from stock (Unsplash/Pexels only) before that iteration's ICP review — the ICP never reviews placeholder slots.
- Each iteration's ICP score is therefore on the real artifact; an image that breaks the design is caught that iteration and re-sourced (different image, same intent) the next pass.
- No AI image generation; no providers beyond Unsplash and Pexels.
