#!/usr/bin/env python3
# AMI meeting reference builder: per-speaker NXT words XML -> one time-sorted
# word stream (single line, no trailing newline). Skips punctuation tokens,
# truncated words and mispronounced words; html-unescapes entities.
# Overlapping words with identical starttime are ordered by speaker file order
# (A,B,C,D,E); exact tie order is arbitrary and shifts WER by <0.1%.
# Corpus: AMI Meeting Corpus, CC BY 4.0, https://groups.inf.ed.ac.uk/ami/corpus/
import sys, glob, html
from xml.etree import ElementTree as ET
ann, meeting = sys.argv[1], sys.argv[2]
words = []
for f in sorted(glob.glob(f"{ann}/words/{meeting}.*.words.xml")):
    root = ET.parse(f).getroot()
    for w in root.iter('w'):
        if w.get('punc') == 'true' or w.get('trunc') == 'true' or w.get('mispronounced') == 'true':
            continue
        st = w.get('starttime')
        t = (w.text or '').strip()
        if not t or not st:
            continue
        words.append((float(st), html.unescape(t)))
words.sort(key=lambda x: x[0])
sys.stdout.write(" ".join(w for _, w in words))
