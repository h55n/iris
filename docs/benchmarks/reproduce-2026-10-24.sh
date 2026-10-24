#!/bin/bash
# Reproduce the 2026-10-24 Iris long-audio benchmark suite from scratch.
# All inputs are free public licensed corpora, re-downloadable; results land in
# docs/benchmarks/2026-10-24-<leg>.json (metrics only, no raw corpus transcripts).
# Needs: ffmpeg, cmake, python3 + jiwer, ~6GB disk, 2 CPU / 1GB RAM (slow but works).

# --- engine: whisper.cpp CLI (same engine the app ships) ---
git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git vendor/whisper.cpp
(cd vendor/whisper.cpp && cmake -B build -DWHISPER_BUILD_TESTS=OFF && cmake --build build -j$(nproc) --target whisper-cli)

# --- models (hf.co/ggerganov/whisper.cpp + ggml-org/whisper-vad) ---
mkdir -p models && cd models
for m in ggml-tiny.en.bin ggml-base.en.bin ggml-base.bin ggml-small.bin; do
  curl -sL --retry 3 -O "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$m"; done
curl -sL --retry 3 -o ggml-silero-v6.2.0.bin "https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin"
cd ..

mkdir -p /tmp/bench/{ami,mucs/sample,fleurs}
# --- AMI Meeting Corpus, CC BY 4.0, https://groups.inf.ed.ac.uk/ami/corpus/ ---
(cd /tmp/bench/ami && for p in a b c d; do curl -sL --retry 3 -O "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2008$p/audio/ES2008$p.Mix-Headset.wav"; done \
 && curl -sL --retry 3 -O "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip" \
 && unzip -q -o ami_public_manual_1.6.2.zip -d ann)
# refs: per-speaker NXT words XML -> time-sorted word stream, punc tokens skipped, html-unescaped
# abc90: ffmpeg concat of a+b-c Mix-Headset wavs -> 89.6-min compilation; ref = concat of the 3 refs

# --- MUCS 2021 Hindi-English sub-task2 test, CC BY-SA 4.0, https://openslr.org/104 ---
(cd /tmp/bench/mucs && curl -sL --retry 3 -O "https://www.openslr.org/resources/104/Hindi-English_test.tar.gz" && tar xzf Hindi-English_test.tar.gz)
# samples: first N seconds of utterances in file order (transcripts/segments + text), 30-min and 60-min

# --- FLEURS hi_in bn_in ta_in es_419, CC BY 4.0, https://huggingface.co/datasets/google/fleurs ---
# per language: data/<L>/test.tsv + data/<L>/audio/test.tar.gz; bounded 30-min concat (col2=file, col4=raw transcript, col6=num_samples)

# --- run: python3 run_one.py <audio> <model> <lang> <out.json> per leg via iris.transcribe
# (repo product path: whisper-cli -l <lang> -oj, + silero VAD when present), then
# jiwer full-transcript WER (lowercase, strip punctuation) vs the ref.
