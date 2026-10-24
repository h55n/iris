#!/usr/bin/env python3
# FLEURS bounded test-subset builder: takes test.tsv rows in order until
# <minutes> of audio (num_samples/16000), writes concatenated wav (16kHz mono)
# and one-line reference from the NORMALIZED transcript column (col 4),
# whitespace collapsed, space-joined.
# Corpus: FLEURS, CC BY 4.0, https://huggingface.co/datasets/google/fleurs
import sys, subprocess, os
tsv, audio_dir, minutes, outwav, outref = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
acc, picked = 0.0, []
for l in open(tsv, encoding='utf-8'):
    c = l.rstrip('\n').split('\t')
    if acc >= minutes * 60:
        break
    acc += int(c[5]) / 16000.0
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
