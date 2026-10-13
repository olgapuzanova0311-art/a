"""Субтитры и паузы по речи (faster-whisper).

python agent/tools/subs.py srt input.mp4 out.srt [--words 4]   субтитры короткими фразами (для рилс по 3-5 слов)
python agent/tools/subs.py ass input.mp4 out.ass [--words 3]   субтитры для рилс: крупные, по центру, жёлтая подсветка текущего слова
python agent/tools/subs.py silences input.mp4 [--gap 0.6]      интервалы речи без пауз (JSON) для вырезания тишины
python agent/tools/subs.py text input.mp4                     просто расшифровка
"""
import json, os, sys
from pathlib import Path

DATA = Path(os.environ.get('DATA', '/data'))


def words(path):
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get('WHISPER_MODEL', 'small'), device='cpu', compute_type='int8',
                     download_root=str(DATA / 'models'))
    segs, _ = m.transcribe(str(path), language='ru', word_timestamps=True, vad_filter=True)
    out = []
    for s in segs:
        for w in s.words or []:
            out.append((w.start, w.end, w.word.strip()))
    return out


def ts(t, ass=False):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h}:{m:02d}:{s:05.2f}' if ass else f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')


def chunks(ws, n):
    cur = []
    for w in ws:
        cur.append(w)
        if len(cur) >= n or w[2].endswith(('.', '!', '?', ',')):
            yield cur; cur = []
    if cur:
        yield cur


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd'); ap.add_argument('src'); ap.add_argument('out', nargs='?')
    ap.add_argument('--words', type=int); ap.add_argument('--gap', type=float, default=0.6)
    a = ap.parse_args(argv)
    cmd, out = a.cmd, a.out
    ws = words(a.src)
    if cmd == 'text':
        print(' '.join(w[2] for w in ws))
    elif cmd == 'srt':
        n = a.words or 4
        lines = [f'{i}\n{ts(c[0][0])} --> {ts(c[-1][1])}\n{" ".join(w[2] for w in c)}\n' for i, c in enumerate(chunks(ws, n), 1)]
        Path(out).write_text('\n'.join(lines), encoding='utf-8')
        print(out)
    elif cmd == 'ass':
        n = a.words or 3
        head = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n'
                'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, '
                'ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                'Style: R,Oswald,96,&H00FFFFFF,&H001A6BFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,80,80,520,1\n\n'
                '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
        ev = []
        for c in chunks(ws, n):
            for k, cur in enumerate(c):
                end = c[k + 1][0] if k + 1 < len(c) else c[-1][1]
                txt = ' '.join(('{\\c&H1A6BFF&}' + w[2].upper() + '{\\c&HFFFFFF&}') if w is cur else w[2].upper() for w in c)
                ev.append(f'Dialogue: 0,{ts(cur[0], True)},{ts(end, True)},R,,0,0,0,,{txt}')
        Path(out).write_text(head + '\n'.join(ev) + '\n', encoding='utf-8')
        print(out)
    elif cmd == 'silences':
        gap = a.gap
        keep, start, prev = [], None, None
        for a, b, _ in ws:
            if start is None:
                start = max(0, a - 0.1)
            elif a - prev > gap:
                keep.append([round(start, 2), round(prev + 0.15, 2)]); start = max(0, a - 0.1)
            prev = b
        if start is not None:
            keep.append([round(start, 2), round(prev + 0.2, 2)])
        print(json.dumps(keep))
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:]) if len(sys.argv) > 2 else print(__doc__)
