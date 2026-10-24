#!/usr/bin/env python3
# FLEURS bounded test-subset builder: takes test.tsv rows in order until
# <minutes> of audio (num_samples/16000), writes concatenated wav (16kHz mono)
# and one-line reference from the NORMALIZED transcript column (col 4),
# whitespace collapsed, space-joined.
# Corpus: FLEURS, CC BY 4.0, https://huggingface.co/datasets/google/fleurs
import sys, subprocess, os
tsv, audio_dir, minutes, outwav, outref = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
# Optional 6th arg: comma-separated earlier split minutes to consume first,
# e.g. "30" for dev (skip baseline), "30,15" for held-out (skip baseline+dev).
# Earlier phases replay the exact baseline rule (rows in order, stop once the
# accumulated duration crosses the phase budget; no dedup), so a boundary row
# belongs to exactly one split. In the pick phase, rows whose normalized text
# appeared in an earlier phase are excluded (same sentence, another speaker);
# inside the pick phase the original no-dedup rule is kept.
skip_plan = [float(x) * 60 for x in sys.argv[6].split(",")] if len(sys.argv) > 6 else []
acc, picked, earlier_texts = 0.0, [], set()
phase = 0  # phase 0 replays the baseline rule: raw rows, no text exclusion
for l in open(tsv, encoding='utf-8'):
    c = l.rstrip('\n').split('\t')
    if len(c) < 6:
        continue
    dur = int(c[5]) / 16000.0
    text = " ".join(c[3].split())
    if skip_plan:
        # replay earlier split k: exclude texts recorded by phases < k (none for
        # the baseline phase, keeping it byte-identical to the committed input)
        if phase > 0 and text in earlier_texts:
            continue
        earlier_texts.add(text)
        acc += dur
        if acc >= skip_plan[0]:
            skip_plan.pop(0)
            acc = 0.0
            phase += 1
        continue
    if text in earlier_texts:
        continue
    if acc >= minutes * 60:
        break
    acc += dur
    picked.append((c[1], c[3]))
with open(outref, "w", encoding='utf-8') as f:
    f.write(" ".join(" ".join(t.split()) for _, t in picked))
lst = outwav + ".concat.txt"
with open(lst, "w") as f:
    for fn, _ in picked:
        f.write(f"file '{os.path.abspath(os.path.join(audio_dir, fn))}'\n")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", outwav], check=True)
os.remove(lst)
print(f"fleurs subset: {len(picked)} utts, {acc:.0f}s -> {outwav}", file=sys.stderr)
