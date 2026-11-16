# Domain research VS protocol

---

## What domain research is, and isn't

Domain research is the body of adjacent, contextual, and archival material that surrounds the brief's domain — everything a practitioner in that field would read, browse, and have absorbed over time. It is studied for the conventions, aesthetic registers, and material culture of the field — not for competitive benchmarking.

**Domain research IS:**
- Adjacent-domain references: neighboring crafts, disciplines, or industries whose visual languages carry relevant formal properties (e.g., ceramics adjacent to textile craft, or glassblowing documentation)
- Audience-habit references: where the actual users of the product spend time, what they browse, what they trust, what ambient design context they carry into any interaction
- Material and technical references: process documentation, maker archives, spec sheets, physical artifact photography, supply-chain imagery — the backstage material of the domain
- Archival references: historical documentation, museum records, vitrine cards, trade catalogues, period magazines specific to the domain — the visual grammar that accumulated before the current design language

**Domain research IS NOT:**
- Direct competitors — those are handled by `competitor-vs-protocol.md`. Competitor study is a separate step with its own pool, sample, and judgment table structure.
- Off-genre conceptual framings — those are handled by `framing-protocol.md` and the Seeds VS step. The framing is the conceptual lens; domain research is the material context inside which the product lives.

**Worked contrast:**

For a Mashiko ceramics e-commerce brief:

- **Domain research**: kiln archives, glaze chemistry references, museum vitrine cards, where ceramics buyers actually browse on their lunch break.
- **Competitors**: Heath Ceramics, MUJI craft section.
- **Framing-seeds (if framing = "sensory / petrichor")**: petrichor field recordings, wet basalt textures, geosmin molecule diagrams.

These three categories are orthogonal. A glaze chemistry reference goes in the domain bank. Heath Ceramics goes in the competitor bank and gets a converge/diverge table. Wet basalt texture goes in the framing seeds. None of these cross-contaminate. Mixing them degrades the specificity of each bank and produces builds that feel researched but not directed.

**Brief-conditioned, not framing-conditioned.** Domain research is conditioned on what the brief's domain actually is — its materials, audiences, history, and adjacent industries. It is not conditioned on the framing applied to the build. A Mashiko ceramics brief with a "petrichor sensory" framing still has kiln archives, glaze chemistry, and ceramics-buyer browsing habits as its domain research pool. Changing the framing to "West African indigo resist-dyeing logic" does not change the domain research pool; it changes only the framing seeds. The domain research pool for any ceramics brief is drawn from the ceramics world regardless of the framing angle. This is the same separation rule that applies to competitors — the brief's market context is independent of the framing's conceptual angle.

---

## Generation procedure

Generate 20 domain reference candidates. Each entry is a name or descriptor, ≤6 words total. Tag each with a band — canonical / mid / long-tail.

Band-count target (the 4/8/8 spread):
- ~4 canonical (the obvious sources a practitioner would name first; important to include so the pool is grounded)
- ~8 mid-tier (solid domain references — respected trade archives, niche vertical publications, regional institutions, adjacent material culture)
- ~8 long-tail (non-Western sources, archival references outside the mainstream Western design canon, micro-vertical publications, audience-habit references that are ambient rather than prestigious)

The long-tail band must actively reach beyond Western and English-language sources. For a ceramics domain: Japanese kiln town guild records, Korean celadon restoration documentation, Nigerian pottery trade routes, Indigenous craft revival archives from the Americas or Oceania. The long tail is long-tail precisely because it requires effort to enumerate. Populating it with more Western boutique studios is an enumeration failure.

Band tags are a **spreading instrument for enumeration only** — they guide the model to generate a diverse pool covering canonical, mid-tier, and long-tail bands, and let the critic verify coverage. They are **never applied at sampling time**. The sample below is uniform.

**Pool format** (written to `sampling.md` before sampling):

| idx | reference | band |
|---|---|---|
| 0 | Mashiko kiln town guild archives | canonical |
| 1 | Hamada Shoji studio documentation | canonical |
| 2 | Victoria and Albert ceramics vitrine cards | canonical |
| 3 | Japanese mingei folk craft movement texts | canonical |
| 4 | Leach Pottery Cornwall process records | mid |
| 5 | Smithsonian folk pottery acquisition records | mid |
| 6 | Craft Horizons magazine 1950s–1970s | mid |
| 7 | Ceramics buyer Pinterest board patterns | mid |
| 8 | Etsy ceramics category browse UX | mid |
| 9 | Glaze chemistry reference manuals | mid |
| 10 | Studio Potter journal back catalogue | mid |
| 11 | Museum gift shop browsing habits (ceramics) | mid |
| 12 | Korean Joseon celadon restoration archives | long-tail |
| 13 | Jingdezhen porcelain town trade records | long-tail |
| 14 | Mexican Talavera tile production records | long-tail |
| 15 | West African coil-built pottery documentation | long-tail |
| 16 | Maori whakairo wood/clay crossover archives | long-tail |
| 17 | Indian Khurja pottery cooperative records | long-tail |
| 18 | Aboriginal Australian ochre-clay technique docs | long-tail |
| 19 | Andean pre-Columbian pottery excavation notes | long-tail |

This example pool shows the 4/8/8 structure: indices 0–3 are canonical, indices 4–11 are mid-tier, indices 12–19 are long-tail reaching non-Western and archival sources.

---

## Sample 2 uniformly

After generating the 20-entry pool and writing it to `sampling.md`, ms-sample two domain references without replacement via the **external sampling gate** (see `sampling-protocol.md` §The external sampling gate):

```bash
python3 -c "import random,time,sys; n,k=int(sys.argv[1]),int(sys.argv[2]); s=int(time.time()*1000); print(f'SEED={s}'); print(f'PICKS={sorted(random.Random(s).sample(range(n),k))}')" 20 2
```

The Bash stdout's `PICKS=[i, j]` line gives the two chosen indices. The model does NOT compute the pick internally; the Bash output is the only source of truth. Record command + stdout + resolved picks in `sampling.md` per the audit format.

Both chosen domain references enter the inspiration bank. They do not need to be in the same tier or from the same sub-category of domain material. A sample pairing one canonical archival source with one long-tail audience-habit reference can be more generative than two institutional archives — the contrast in register is productive.

---

## Present + confirm

After sampling, present the full 20-entry pool with band tags, the ms-clock seed, the two chosen indices, and the two chosen domain references. Include a brief justification of why each chosen reference is productive for this brief — what it carries, what audience context or material register it brings, and why studying it informs the build.

For the cross-cutting four-action confirm flow, see `sampling-protocol.md` §The present + confirm pattern. The standard actions apply:

1. **`continue`** — accept both domain refs, advance to next step
2. **`resample`** — draw a new ms-clock seed against the same 20-entry pool (different two refs from the same enumeration)
3. **`choose N, M`** — manual override; user specifies two indices from the pool by number
4. **`new options`** — discard the 20-entry pool entirely; re-enumerate a fresh pool of 20 domain references for the brief's domain and present again

Every override is logged in the audit trail with timestamp and reason (if given). The original sampled pair stays in the log alongside the final accepted pair.

---

## Iteration re-sample rule (SOFT EXTENSION)

This is the feature that distinguishes domain research from every other VS step in this skill. All other sampled inputs are fixed at the start of the build: the framing, the designer, the seeds, the constraint, the competitors, the typeface — these do not grow during the critic-loop or ICP-loop iterations. Domain research is the single exception.

**During critic-loop and ICP-loop iterations, the Designer may VS-sample +2 additional domain references if iteration feedback exposes a specific gap** that the original 2 domain refs did not cover.

### Constraints on iteration additions

- **Always via VS.** Any addition must go through the full procedure: brainstorm 20 fresh domain reference candidates for the gap exposed, assign band tags, draw a uniform 2-from-20 sample with a new ms-clock seed. No shortcuts. No reaching from memory to name a reference without a fresh enumeration. The purpose of VS here is not bureaucratic — it is to force the model to enumerate before it picks, which surfaces candidates it would not have named directly.
- **Cap of +2 per iteration.** A single iteration can add at most 2 domain references (one VS draw of 2).
- **Cap of +6 additional across all iterations.** Across the full build lifecycle — all critic-loop and ICP-loop iterations combined — the domain research bank can grow by at most +6 beyond the original 2. The original 2 plus up to 6 additions gives a maximum domain reference pool of 8.
- **Original picks stay.** The original 2 sampled references are never replaced by iteration additions. Iteration additions are additive, not substitutive.
- **Audit trail per addition.** Each iteration addition gets its own section in `sampling.md` — a new header indicating which iteration triggered it, with the full 20-candidate pool for that draw, the seed, the chosen indices, and the user confirmation actions recorded.

### Present + confirm for iteration additions

Iteration-time additions go through the same present + confirm flow as the initial sample. The agent presents the 20 fresh candidates, the seed, the chosen pair, and a justification tying each chosen ref directly to the gap identified in iteration feedback. The user can resample, override, or reject the addition entirely.

Rejection is a valid outcome. If the user decides the gap does not warrant a domain ref addition — or that the gap should be addressed by design judgment rather than a new reference — the addition is declined and no new ref enters the bank. The agent must not re-propose the addition in the same iteration.

### Justification requirement

When the Designer requests an iteration addition, they must state which specific piece of iteration feedback motivated it. The justification must be concrete and traceable.

**Accepted justification:** "I need a warmer empty-state reference because ICP iteration 2 said the empty state felt cold — specifically, the `zero-results` panel was described as clinical. I want to sample 2 domain refs from the material/texture end of the pool to find a register that changes this."

**Rejected justification:** "I want to add more references because the build feels thin." — This is not a specific gap. No iteration feedback is cited. No design element is named. The agent must refuse this request and ask the Designer to identify the specific element and the specific feedback that exposed the gap.

The standard for acceptance is: could a reader of `sampling.md` trace this addition to a specific critic or ICP feedback comment? If yes, the justification is valid. If no, it is not.

---

## How the Designer uses domain refs

Domain references enter the inspiration bank as regular references — studied alongside the framing seeds, designer persona, and constraint. They do not require a converge/diverge judgment table (unlike competitors). Domain material is borrowed from with judgment, not against a binary verdict structure.

**Borrowing summary tracking.** The borrowing summary (see `borrowing-summary-protocol.md`) tracks per-reference contributions across all references in the inspiration bank, including domain refs. For each domain ref from which something is borrowed, the Designer records:
- Which named visual element was borrowed (e.g., "grid density rhythm," "label typographic register," "surface texture treatment")
- The CSS selector or build location where that borrowed element appears
- A screenshot citation confirming the element is present in the built artifact

**No converge / diverge table.** Unlike competitors, domain refs do not get a verdict column. There is no concept of "table-stakes" for a domain reference the way there is for a competitor — a domain ref is studied for what it offers, not for the conventions it enforces on users. The Designer borrows selectively and records what was taken; they are not required to account for what was not taken or to justify divergence from it. The absence of a borrowed element from a domain ref is unremarkable. The presence of a borrowed element must be documented.

**Iteration additions use the same tracking structure.** Domain refs added during iterations enter the borrowing summary under the same schema — reference name, element borrowed, selector, screenshot citation. The iteration number is noted alongside the reference entry so the audit trail can distinguish original picks from iteration additions.

**Domain refs are never cited for brand sentiment or "feeling."** A domain ref earns its place in the borrowing summary only when a specific visual element can be named and located in the build. "The ceramics archive influenced the overall warmth" is not a borrowing record — it is a mood note. The record is: "Hamada Shoji studio documentation → dense-packed label placement → `.product-meta .label-row` → screenshot: ceramics-detail-v2.png." If a domain ref was studied but nothing specific was borrowed from it, it still appears in the bank (it conditions the Designer's eye), but it does not appear in the borrowing summary.