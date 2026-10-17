# Typography VS protocol

---

## Why typography needs its own VS layer

Typography is the layer where the model's default canon is most deeply grooved. Ban Söhne and the model reaches for Reckless Neue. Ban that and it finds Domaine Display. Ban that and it lands on GT Sectra. The premium-type defaults form a layered canon with deep bench depth — every foundry darling of the 2015–2025 era is sitting one ban away from the previous one. Without a dedicated VS step, the typography slot reliably fills with a small rotation of prestige faces that carry near-identical register and cultural meaning regardless of what the framing demands.

VS enumeration with anti-canon discipline breaks this cycle. Our experiments showed that dropping Söhne from the typography slot via VS reduced typography Jaccard similarity from 0.10 → 0.018 across 5 briefs: frontend-design vanilla used Söhne in 9/10 cross-prompt pairs; the VS layer eliminated it entirely. The mechanism is not prohibition alone — prohibition just promotes the next canonical face. The mechanism is enumeration: by forcing 15 candidates across canonical, mid, and long-tail bands, and sampling uniformly across all 15, the probability of landing on any single tier drops sharply. The long-tail must be populated with genuinely non-obvious choices, not just the ninth-most-common prestige face.

This is also why typography gets its own protocol file rather than being handled under `sampling-protocol.md`. The typographic canon is deep enough that the generic VS band-spread instructions are insufficient — without explicit banned-list enforcement and without named non-canon source foundries, the model reliably populates the long-tail with Graphik, Aktiv Grotesk, or Canela, which are functionally canonical. The dedicated protocol carries both the ban list and the source list that are necessary to make the long-tail genuinely non-canon.

---

## Framing-conditioned

The chosen framing from `framing-protocol.md` is the lens that conditions which typefaces are plausible candidates. Typography VS pools are not generated from scratch against the brief; they are generated against the confirmed framing, and the framing carries the register, historical territory, and material logic that makes certain typefaces earn their place in the pool.

A "Sicilian funeral band" framing pulls toward Romana Bold, Caslon Black, Tusker Grotesk, and Cardinal Fruit — faces that carry weight, ceremony, and age. A "Berlin techno club lighting booth" framing pulls toward PP Neue Machina, Cardboard, Apoc Revelations, and single-purpose industrial cuts — faces built for hostile contrast and machine legibility. These are not aesthetic preferences; they are logical consequences of the framing's territory. The framing is the upstream variable. Typography candidates emerge from it. A typeface that would be a strong choice in one framing may have zero plausibility in another even if its visual quality is identical.

A "Maine fishing-shack construction logic" framing pulls toward vernacular sans-serifs, compressed grotesks, and hand-stencil-adjacent display faces — faces that carry weather-worn utility, not graphic-design ambition. A "mycelial network growth logic" framing pulls toward organic, spore-like display cuts, irregular optical sizing, and typefaces with biological edge quality. Neither of these framings has a clean answer from the prestige-type catalogue. The framing is the constraint that makes the candidate generation non-trivial.

When generating candidates, evaluate each proposed face against the question: does this typeface's register, material logic, historical context, and cultural positioning serve this framing — not just aesthetically, but conceptually? A Klim Heldane may serve an "archival magazine editorial" framing perfectly and have nothing to contribute to a "West African resist-dyeing logic" framing. The framing gate is applied before any candidate enters the pool. A face that cannot be argued into the framing with a concrete rationale does not belong in the enumeration, regardless of its design quality or cultural prestige.

---

## Generation procedure

Generate exactly **15 candidates**. Each candidate is formatted as:

```
"Typeface Name — role"
```

For example: `"Reckless Neue — display"`. Valid roles: display, body, mono, caption, accent, headline, subhead.

Each candidate is tagged with a band — canonical / mid / long-tail. The band is a spreading instrument for enumeration only — it is never applied at sampling time. It guides the model to populate the pool with genuine spread across the bands and lets the critic verify coverage; the draw itself is uniform over all 15.

Required band spread across the 15 candidates:

- **~3 canonical** — the faces that most directly serve the framing's register and territory. They may include well-known or prestige faces if those faces genuinely fit the framing.
- **~6 mid-band** — solid matches, interesting stretches, faces that carry the framing's logic with some productive friction.
- **~6 long-tail** — genuinely unexpected, non-obvious, or historically marginal faces that carry formal or conceptual properties relevant to the framing. This is where anti-canon discipline is enforced.

The "~" is a guide, not a hard constraint: a pool with 3/5/7 or 4/6/5 distribution is acceptable. What is not acceptable is a long-tail that collapses into slightly-less-common prestige faces. If the long-tail reads like a B-list of the same foundry canon, regenerate it.

Common anti-patterns to reject during generation:

- **The prestige-ladder long-tail**: Graphik → Aktiv Grotesk → Canela → Adieu → Freight Display. All of these are well-known and culturally legible within the design world. None qualify as long-tail.
- **The foundry sweep**: all 6 long-tail entries from a single foundry (e.g., all from Klim, all from Commercial Type). Foundry diversity is required; a sweep signals that the model is not ranging wide enough.
- **Role collapse**: all 15 candidates labeled "display." If the framing calls for body text or mono, those roles must appear in the pool. A pool without body candidates cannot serve a full typographic system.
- **Framing-agnostic pool**: the pool reads the same regardless of which framing was chosen. If swapping in a different framing would produce the same pool, the pool is not framing-conditioned — it is just the model's default type vocabulary.

Each candidate should include a one-line rationale in the generation notes (not in the table itself) explaining why it earns its band in the context of the confirmed framing. This rationale is for model-side audit during generation; it is not shown to the user unless they request it. The rationale prevents band assignment from being arbitrary — if you cannot articulate why a face belongs in its band (canonical vs mid vs long-tail) in the context of this specific framing, the band is not grounded.

Example pool shape for a "Dub Jamaica sleeve design" framing:

```
| idx | typeface — role          | band      |
|-----|--------------------------|-----------|
|  0  | Tusker Grotesk — display | canonical |
|  1  | Caslon Black No.2 — display | canonical |
|  2  | Romana Bold — headline   | canonical |
|  3  | PP Neue Machina — body   | mid       |
|  4  | Heldane Display — display | mid       |
|  5  | Cardinal Fruit — accent  | mid       |
|  6  | Freight Display — body   | mid       |
|  7  | Pitch — mono             | mid       |
|  8  | Domaine Display — display | mid       |
|  9  | Marcia — display         | long-tail |
| 10  | Eckmann Schrift — display | long-tail |
| 11  | Or Type Freak — display  | long-tail |
| 12  | Velvetyne Outward — body | long-tail |
| 13  | ITF Signifier — body     | long-tail |
| 14  | Cardinal Fruit Dark — display | long-tail |
```

Write candidates to `sampling.md` under `## Typography VS / Candidate pool` in the table format shown above.

---

## Banned long-tail list

Long-tail entries must NOT include any of the following:

```
Söhne / Söhne Breit / Söhne Mono
GT America / GT America Mono / GT Sectra / GT Alpina
Inter / Roboto / Arial
Tiempos Text
Berthold Akzidenz / Berthold Akzidenz-Grotesk
ABC Diatype / ABC Diatype Mono
Suisse Int'l
Founders Grotesk
IBM Plex Mono
Berkeley Mono / JetBrains Mono
```

These faces are banned from the long-tail because they are canonical by definition — their cultural meaning is known, their design-world associations are fixed, and placing them in the long-tail is a category error. A long-tail entry must be genuinely unexpected relative to the framing's canonical territory; none of the above faces qualify.

Mid-band (0.40–0.85) entries CAN include these if the framing genuinely calls for them. A framing built around Swiss corporate systems design may legitimately place Berthold Akzidenz-Grotesk in the mid-band at 0.60. A framing centered on German digital infrastructure may place GT America Mono at 0.55. The ban is scoped to the long-tail only. The long-tail is the anti-canon strict zone; the mid-band is governed by framing fitness, not by prohibition.

Verify the ban before presenting the pool. If any banned face appears in a long-tail slot, remove it and replace it with a non-canon alternative before the pool is shown to the user.

---

## Where to reach for non-canon

For long-tail candidates, the model should preferentially reach into these foundries and territory categories rather than cycling through the prestige-foundry catalogue:

- **Indian Type Foundry** — wide multilingual and Latin catalogue with faces that carry non-Western spatial logic
- **Pangram Pangram** — broad display range including Neue Machina and Neue Montreal, plus less-circulated cuts
- **Or Type (Iceland)** — small Icelandic foundry with formally unusual Latin and experimental weights
- **Tipo Pèpel** — Latin American foundry with strong display and blackletter-influenced cuts
- **Velvetyne Type Foundry** — open-source foundry with genuinely experimental and non-commercial-register faces
- **Studio Triple** — display and experimental typefaces that resist clean genre assignment
- **Schick Toikka** — Finnish foundry with unusual optical sizing logic and non-Anglo cultural positioning
- **Klim's lesser-used cuts** — Domaine, Pitch family, and Heldane are less defaulted-to than Tiempos; they belong in mid or long-tail depending on framing, not in the canonical slot
- **Historical revivals** — Romana, Marcia, Caslon Black No.2, Eckmann Schrift, Cardinal Fruit; faces with specific historical and material contexts that resist generic deployment
- **Single-purpose displays** — DSEG7 (seven-segment LCD), Apollo Stencil, monotype slab specimens; faces built for a specific production context that can be formally productive outside it
- **Brief-domain specimens** — NASA Mission Number for tech/aerospace briefs, Drum Major for funeral or processional contexts, and other faces with strongly domain-specific cultural positioning

The goal is not novelty for its own sake. It is that these sources are under-represented in the default canon, which means a pool drawn from them is more likely to produce picks that the brief has not already been surrounded by in training data. The long-tail is where genuine surprise lives.

A useful self-check when generating long-tail entries: could you find this typeface recommended on a popular design blog in the last five years? If yes, it is probably already canon-adjacent and should move to mid-band or be replaced. The long-tail should contain faces that require knowing a foundry directly, having encountered them in a historical specimen book, or being embedded in a specific design subculture — not faces that are merely less popular than the top ten prestige choices.

---

## Sample 2-4 uniformly

With the 15-candidate pool written to `sampling.md`, ms-sample between 2 and 4 candidates via the **external sampling gate** (see `sampling-protocol.md` §The external sampling gate). The number of picks is itself sampled, so this step issues **two** Bash calls:

```bash
# Step 1: pick k ∈ {2, 3, 4}
python3 -c "import random,time; s=int(time.time()*1000); print(f'SEED_K={s}'); print(f'K={random.Random(s).randint(2,4)}')"
```

Then use the printed `K` value in the second call:

```bash
# Step 2: pick K typefaces from the 15-pool (substitute the K value from above)
python3 -c "import random,time,sys; n,k=int(sys.argv[1]),int(sys.argv[2]); s=int(time.time()*1000); print(f'SEED={s}'); print(f'PICKS={sorted(random.Random(s).sample(range(n),k))}')" 15 <K>
```

The model does NOT compute either pick internally. Both Bash stdouts are the only source of truth. Record both commands + both stdouts + resolved K + resolved picks in `sampling.md` per the audit format. Bands are not applied during sampling; every index has equal probability regardless of band. The long-tail entries can only be drawn because they share the same probability as the canon — if the draw were band-weighted, the pool would collapse back toward canonical on every draw.

The chosen picks form the **typography selections** for this build. If k=2 and both picks land on display-role faces, treat the first as the primary display face and the second as an accent. If k=3 or k=4, assign roles based on what the brief requires, overriding the candidate's labeled role if necessary. The Designer subagent has discretion over role assignment at build time.

Record in `sampling.md` under `## Typography VS / Sampled picks`:

```
ms-sample (k):    [SEED_K + K stdout]
ms-sample (picks): [SEED + PICKS stdout]
chosen typefaces: [resolved names from indices]
```

---

## Present + confirm

See `sampling-protocol.md` §The present + confirm pattern for the full four-action protocol (`continue` / `resample` / `choose N` / `new options`) and logging requirements.

Present the full 15-candidate pool with band tags, the two seeds used (for k and for the sample), the value of k, the chosen indices, the chosen typefaces, and a brief justification of why the chosen picks serve the framing and brief. The justification should address each chosen face individually — one sentence per face explaining the framing-specific reason it was in the pool and why the pick is legible.

Special note on user override leverage: typography is the layer most visible to end-users. A color choice or layout constraint operates below the threshold of explicit noticing for most audiences; a typeface is immediately legible as a register signal — even users with no design vocabulary can tell when a typeface reads wrong. Users who care about brand positioning, competitive differentiation, or cultural fit will have the strongest opinions at this step. Override here has higher leverage than at Seeds VS or Constraint VS, and the skill is designed to support it.

Action mapping for the typography step specifically:

- **`continue`** — accept the drawn typefaces; the Designer subagent proceeds to build using them, with discretion over role assignment.
- **`resample`** — draw a new ms-clock seed against the same 15-candidate pool. Different picks, same enumeration. Use when the drawn picks feel wrong but the pool itself is strong.
- **`choose N` or `choose N, M`** — manual override; user selects specific indices from the pool. Use when the user has a specific typographic instinct or a face they want to test. The chosen indices replace the sampled picks entirely.
- **`new options`** — discard the candidate pool entirely; regenerate a fresh 15-candidate pool from the framing and re-present. Use when the entire pool reads as the wrong register for the brief — not just the picked faces but the enumeration itself.

Every override action is logged in `sampling.md` with the original sampled pick alongside the final accepted pick, so the divergence is part of the audit trail. The Designer subagent sees the final accepted picks only; the override history is visible to the user and to future reviewers of `sampling.md`.

In auto mode (see `sampling-protocol.md` §Auto mode), the present + confirm pause is skipped, but the pool, seeds, and chosen picks are still logged to `sampling.md` for audit. Auto mode is not recommended for typography on first builds; the typographic register is consequential enough that human review catches errors that no automated gate can catch.

---

## Re-sample edge case

If the uniform sample lands on a typeface that is on the banned long-tail list — because the model accidentally included a banned face in a long-tail slot despite the generation rule — the Designer must immediately reject the pick and initiate a pool correction:

1. Remove the violating typeface from the candidate pool.
2. Regenerate a replacement candidate for that slot, drawn from the non-canon sources listed above, in the same band.
3. Resample from the corrected 15-candidate pool using a new ms-clock seed.
4. Log the resample event in `sampling.md` with:
   - The violating typeface and its index
   - The reason for rejection (banned long-tail family)
   - The replacement candidate
   - The new seed used for resampling

This bypass is the **only** model-side resample allowed in the typography step. The model cannot resample because it dislikes the pick, because the pick seems mismatched to the framing, or for any other taste-based reason. Those are user actions — `resample` or `choose N` from the present + confirm step. The ban-violation resample is a rule-enforcement action, not a taste action, and is scoped strictly to the case where the pool contains a technical violation.

The distinction matters because it defines where taste authority lives in the skill. The model's taste is not trustworthy enough to warrant silent resampling; that is why the uniform draw exists in the first place. The ban-violation resample is not a taste judgment — it is enforcement of a mechanical rule that the model violated during generation. It is the typographic equivalent of a spell-checker correction, not an editorial decision. Everything that is an editorial decision goes through the user.

Everything else — picks that seem off, picks that feel generic, picks that tension productively against expectation — goes through the user via the standard present + confirm protocol. The model does not override its own draw except for ban violations. Log every such event in `sampling.md` with the reason clearly stated, so the audit trail reflects that the pool correction happened and why.

The expected rate of ban-violation resamples in a well-generated pool is zero. If the generation procedure is followed correctly — with the banned list verified before the pool is presented — the sample will never land on a banned face because no banned face will be in the long-tail. The resample edge case protocol exists as a safety net for generation errors, not as a routine part of the step. If ban-violation resamples are occurring frequently across builds, it is a signal that the generation step is not applying the ban list rigorously and that procedure needs to be corrected at the source rather than patched at the sample stage.

---

*This protocol is the final step in the framing → designer → seeds → constraint → competitors → domain → typography sampling chain. Once typography selections are confirmed, all upstream VS variables are fixed and the Designer subagent proceeds to build.*
