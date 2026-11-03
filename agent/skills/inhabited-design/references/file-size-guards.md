# Image File Size Guards

Critical: subagents WILL break mid-loop without these guards. Empirically verified across multiple runs.

## The problem

The Read tool has a 2000px image dimension limit. Reference images downloaded from real design sites are often larger:
- Awwwards hero shots: 2400×1600 typical
- Tracksmith editorial spreads: 2000+ px
- Apple HIG screenshots: 2880px on retina exports

When a subagent later tries to Read one of these saved images during the build (per the lookback discipline), the tool call fails with:

```
An image in the conversation exceeds the dimension limit for many-image requests (2000px).
Run /compact to remove old images from context, or start a new session.
```

This crashes the subagent silently mid-loop. The build never ships.

## The guards (apply ALL three)

### 1. Format whitelist

Only save these formats:
- `png`, `jpg`, `jpeg`, `gif`, `webp`

Never:
- `svg` — Read tool can't render
- `avif` — Read tool can't render
- `heic`, `heif`, `tiff` — same

If a download URL returns an unsupported format, **skip that reference and pick another**. Don't try to convert.

### 2. Downscale after every download

Use Pillow:

```bash
python3 -c "from PIL import Image; img=Image.open('references/01_x.png'); img.thumbnail((1600,1600)); img.save('references/01_x.png')"
```

Apply to every file immediately after `curl` or `wget`. The `thumbnail` call preserves aspect ratio and only shrinks (no-op if already small).

Target: **≤1600px on the longest edge** (gives headroom under the 2000px limit).

### 3. Verify dimensions before saving the bank

After downloading all references, run:

```bash
python3 -c "
from PIL import Image
import os
d = 'references'
for f in sorted(os.listdir(d)):
    if f.startswith('.'): continue
    p = os.path.join(d, f)
    w, h = Image.open(p).size
    if max(w, h) > 1800:
        print(f'WARN: {f} is {w}x{h} — re-downscale')
    else:
        print(f'OK:   {f}  {w}x{h}')
"
```

If any file warns, re-run the downscale on that file or replace with a smaller variant.

## In the persona file

The Designer persona file should embed these as a hard rule under the "How you work" section. Sample text:

```markdown
**HARD CONSTRAINTS on image format and size** (avoid context errors):
- Only save images in **png, jpg, jpeg, gif, or webp** formats. NEVER svg or avif — Read tool can't display them.
- After download, **always downscale to ≤1600px on the longest edge** before relying on the file.
- If a URL returns SVG or invalid format, skip and pick a different reference.
```

## In the subagent prompts

When spawning Designer subagents, include this guard in the prompt:

```
**HARD CONSTRAINTS on image format and size** (avoid context errors):
- Only save images in png/jpg/jpeg/gif/webp formats. NEVER svg or avif.
- After download, downscale to ≤1600px on longest edge:
  python3 -c "from PIL import Image; img=Image.open('p'); img.thumbnail((1600,1600)); img.save('p')"
- If a URL returns SVG or invalid format, skip it and pick a different reference.
```

## In the ICP review prompts (and Designer pre-handoff verification)

Both subagents MUST capture viewport-bounded screenshots, not only DOM snapshots. The previous "DO NOT take screenshots" rule was wrong — it banned the verification that catches the bugs DOM cannot see, and produced a silent failure mode where ICP scored builds 7×10 that had visible P0 bugs (inline-span overflow, sticky-rail / footer collision, marker overlapping body text). The empirical case is documented in this skill's iteration-loop.md.

**The bounded-screenshot gate (Jesse Vincent gate pattern — BLOCKING):**

> **Trigger:** About to score / about to return "build done".
> **Condition:** Viewport-bounded screenshot files exist on disk at `iter_{N}/screens/` (or `iter_{N}/designer/screens/` for Designer pre-handoff), AND each has been Read.
> **Next action:** BLOCKED until the condition is met.

The recipe (subagent prompts should include this verbatim):

```
**Pixel verification — mandatory, blocking gate:**

1. mkdir -p iter_{N}/screens
2. browser_resize 1280 800 (or smaller; NEVER larger than 1280 on longest edge)
3. For each key screen / section / interactive state:
   - browser_take_screenshot filename=iter_{N}/screens/<descriptive_name>.png
   - NEVER fullPage: true (can exceed 2000px even at small viewport)
   - The viewport bound keeps the saved PNG well under the 2000px Read limit.
4. Read the saved screenshot with the Read tool. Look at pixels.
5. browser_snapshot for DOM accessibility tree.
6. browser_evaluate for computed styles where needed.

Cite specific pixel observations in your feedback, alongside DOM observations. "The reveal panel renders as a black bar below the thumbnail at idle" — that's a pixel observation; cite which screenshot showed it.

The 2000px Read-tool limit applies to images in active conversation context, not files on disk that you bring in with the Read tool. Viewport-bounded PNG files are 100-300KB and Read fine. The filename= parameter writes to disk; the response payload can be discarded (use Read on the file path afterward to bring pixels into context deliberately).
```

**Why this works (the file-vs-context distinction):**
- `browser_take_screenshot` *without* `filename`: returns image bytes in the response, dumps into conversation context. This is what blew context on prior runs.
- `browser_take_screenshot filename=path`: writes to disk; the conversation gets a small ack message. Pixels are only loaded into context when you Read the saved file deliberately.
- Bounded viewport (≤1280×800) keeps the saved PNG well under the 2000px Read limit, so the Read call doesn't crash.

The combination — bounded viewport + filename + deliberate Read — gives the agent pixel verification without context bloat.

## Why we know this matters

In the experiment that produced this skill:
- **Run without guards:** 3 of 6 parallel agents crashed mid-build with the 2000px error
- **Run with downscale guard only:** 1 of 3 still crashed (saved screenshots OF the build during review hit the limit)
- **Run with all 3 guards (downscale + format whitelist + browser_snapshot for review):** 3 of 3 completed

These guards are not optional.

## Edge cases

### "I really need this SVG reference"

Convert to PNG first, then save:
```bash
# rasterize via Inkscape or rsvg-convert
rsvg-convert -w 1600 in.svg -o references/01_x.png
```

### "The screenshot was taken at high DPR and is huge"

Re-take at lower viewport, or downscale after capture:
```bash
python3 -c "from PIL import Image; img=Image.open('p'); img.thumbnail((1600,1600)); img.save('p')"
```

### "Pillow isn't installed"

Use ImageMagick:
```bash
convert references/01_x.png -resize '1600x1600>' references/01_x.png
```

Or curl-side cap (rough — doesn't downscale, just rejects oversize files):
```bash
curl --max-filesize 2000000 -L -o references/01_x.png URL
```

## Test before launching the loop

After the bank is built, before invoking iteration:
- Read every file in references/ (Read tool, no offset/limit) — verify each loads
- If any fails, downscale or replace before launching the loop

5 seconds of verification beats 20 minutes of crashed iteration.
