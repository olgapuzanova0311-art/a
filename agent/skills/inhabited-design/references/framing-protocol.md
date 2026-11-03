# Framing protocol (bankless — generate to pole quotas)

A framing is a **conceptual lens** — a sentence (6–15 words) describing the abstract angle, register, or constraint that conditions every subsequent design decision. Not a reference. Not a style tag. Not a one-word adjective like "minimalist."

The framing is the **master conditioning variable** for the VS pipeline. Every downstream VS step (Designer, Seeds, Constraint, Competitors, Typography) is conditioned on it; the variance leverage of every other step compounds against this pick.

## The bankless approach

This variant replaces the curated 200-framing bank with **live generation to a pole table**. Per run, the model generates ≈40 framings distributed across 11 style-poles per the quotas in `framing-poles.md` (scientific/instrument capped at 2/40 ≈ 5%), then ms-samples 1 from those 40 via the external Bash gate.

The bet under test: the bank's diversity was carried by its **structural rules** (pole quotas + scientific cap + ban-list + reach-beyond mandate), not by its 200 hand-written entries. Live generation to the same rules should hold the same diversity without the maintenance burden — *if the model honors the quotas and reaches genuinely non-canon within each pole.* The A/B harness measures whether it does (cross-run Jaccard + pole concentration vs. the banked control).

## Procedure

### Step 1 — Read the pole table

`Read` `framing-poles.md` in full. The pole quotas, the scientific cap, the ban-list, and the reach-beyond mandate are the anti-attractor mechanism — honor them exactly.

### Step 2 — Generate ≈40 framings to quota

Generate a fresh pool of ≈40 framings distributed per the pole quotas (scientific/instrument **≤2**). Each framing: 6–15 words, an abstract angle/lens, brief-appropriate but reaching for genuine diversity per the reach-beyond mandate. **Tag each candidate with its pole.** Honor the ban-list (no Swiss/Dutch graphic-design canon, no generic single-word labels, no the-brief's-own-category, no excess scientific).

### Step 3 — Brief-fitness filter + quota self-check

Apply the **marketing-director test** to each generated framing:

> *"If a marketing director received this conceptual angle as a creative direction, could they see how it serves the product's actual job — even if they wouldn't have chosen it themselves?"*

Drop any framing that inverts the emotional register, destroys positioning, or makes the brief's job impossible; regenerate a replacement **from the same pole** to hold the quota. Then run the **quota self-check**: scientific/instrument ≤2, total ≈40, each pole ≈ its quota. Write the ≈40 framings to `sampling.md` under `## Framings`, each with its pole tag, and record the per-pole counts.

### Step 4 — ms-sample 1 via the external Bash gate

```bash
python3 -c "import random,time,sys; n,k=int(sys.argv[1]),int(sys.argv[2]); s=int(time.time()*1000); print(f'SEED={s}'); print(f'PICKS={sorted(random.Random(s).sample(range(n),k))}')" 40 1
```

The stdout's `PICKS=[i]` line gives the chosen framing index (0-indexed) into the ≈40-pool. Record command + stdout + resolved pick (with its pole) in `sampling.md` per the audit format in `sampling-protocol.md`.

### Step 5 — Lock + status-write

Write the chosen framing to `sampling.md` under `## Framing locked`: pole, framing text verbatim, brief justification of why it earns its keep for this brief + ICP, and the per-pole pool counts (for the pole-concentration audit). Then `Edit` `pipeline_status.md` rows 2–4 → `done`.

## Present + confirm

Present the chosen framing and wait for user confirmation. See `sampling-protocol.md` §The present + confirm pattern for the 4-action protocol (`continue` / `resample` / `choose N` / `new options`).

**`new options` in this protocol**: regenerate a fresh pool of ≈40 framings to the same pole quotas.

## Note on provenance

The banked variant logged a `bank idx` per framing so the filter was replayable against the fixed 200-bank. The bankless variant has no fixed bank, so the audit record is the **generated ≈40-pool itself** (written to `sampling.md` with pole tags) plus the Bash seed. A given run is fully auditable from `sampling.md`; cross-run pool reproducibility is intentionally gone (the pool is freshly generated each run — that is the source of diversity under test).
