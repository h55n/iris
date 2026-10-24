#!/usr/bin/env python3
# MUCS 2021 Hindi-English sub-task2 test sampler: takes utterances in segments
# file order until <minutes> of audio, writes the concatenated wav (16kHz mono)
# and the one-line reference (whitespace-collapsed transcripts, space-joined).
# Optional 5th arg: comma-separated earlier phase minutes; those phases are
# replayed with the same rule first and their utterances excluded, so later
# slices are utterance-disjoint from earlier ones (dev/held-out splits).
# Utterances are unique in MUCS (no sentence-pool reuse), so text disjointness
# follows from utterance disjointness.
# Corpus: MUCS 2021, CC BY-SA 4.0, https://openslr.org/104
import sys, subprocess, os
test, minutes, outwav, outref = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
earlier = [float(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 and sys.argv[5] else []
text = {}
for l in open(f"{test}/transcripts/text", encoding='utf-8'):
    k, v = l.rstrip('\n').split(None, 1)
    text[k] = v
segs = []
for l in open(f"{test}/transcripts/segments", encoding='utf-8'):
    utt, wav, s, e = l.split()
    segs.append((utt, wav, float(s), float(e)))
used = set()
def pick(limit_min):
    acc, picked = 0.0, []
    for utt, wav, s, e in segs:
        if acc >= limit_min * 60:
            break
        if utt in used:
            continue
        acc += e - s
        picked.append((utt, wav, s, e))
    return picked
for m in earlier:
    for utt, _, _, _ in pick(m):
        used.add(utt)
picked = pick(minutes)
with open(outref, "w", encoding='utf-8') as f:
    f.write(" ".join(" ".join(text[u].split()) for u, _, _, _ in picked))
lst = outwav + ".concat.txt"
with open(lst, "w") as f:
    for utt, wav, s, e in picked:
        f.write(f"file '{os.path.abspath(os.path.join(test, wav + '.wav'))}'\ninpoint {s}\noutpoint {e}\n")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", outwav], check=True)
os.remove(lst)
print(f"mucs sample: {len(picked)} utts, {sum(e-s for _,_,s,e in picked):.0f}s -> {outwav}", file=sys.stderr)
