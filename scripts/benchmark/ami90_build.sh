#!/bin/bash
# AMI-90 builder: downloads ES2008 a,b,c Mix-Headset wavs + manual annotations,
# builds per-part references and the 89.6-min a+b+c compilation (assembled parts,
# session gaps possible) with concatenated reference.
# Corpus: AMI Meeting Corpus, CC BY 4.0, https://groups.inf.ed.ac.uk/ami/corpus/
set -euo pipefail
B=$1; REPO=$2
mkdir -p "$B/ami"; cd "$B/ami"
for p in a b c; do
  [ -f "ES2008$p.Mix-Headset.wav" ] || curl -sL --retry 3 -O "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2008$p/audio/ES2008$p.Mix-Headset.wav"
done
if [ ! -d ann ]; then
  [ -f ami_public_manual_1.6.2.zip ] || curl -sL --retry 3 -O "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip"
  unzip -q -o ami_public_manual_1.6.2.zip -d ann
fi
for p in a b c; do
  python3 "$REPO/scripts/benchmark/ami_ref.py" ann "ES2008$p" > "ES2008${p}_ref.txt"
done
cat ES2008a_ref.txt ES2008b_ref.txt ES2008c_ref.txt > ES2008abc90_ref.txt
printf "file '%s'\nfile '%s'\nfile '%s'\n" "$B/ami/ES2008a.Mix-Headset.wav" "$B/ami/ES2008b.Mix-Headset.wav" "$B/ami/ES2008c.Mix-Headset.wav" > concat_abc.txt
[ -f ES2008abc90.wav ] || ffmpeg -y -v error -f concat -safe 0 -i concat_abc.txt -c copy ES2008abc90.wav
