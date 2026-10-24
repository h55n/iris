#!/bin/bash
# Runs one benchmark leg end to end (CI or local): pinned whisper.cpp build,
# sha256-pinned models, input build from original sources, transcribe via the
# repo product path, WER into docs/benchmarks/. Never commits or pushes.
set -euo pipefail
LEG=$1
REPO=$(cd "$(dirname "$0")/../.." && pwd); cd "$REPO"
B=${WORKSPACE_BENCH:-/tmp/bench-ci}
WPIN=231638a0717b7822784297e5980965ffcec05810  # whisper.cpp, 2026-10-19 - pinned for reproducibility

if [ ! -x vendor/whisper.cpp/build/bin/whisper-cli ]; then
  rm -rf vendor/whisper.cpp
  git clone -q https://github.com/ggml-org/whisper.cpp.git vendor/whisper.cpp
  git -C vendor/whisper.cpp -c advice.detachedHead=false checkout -q $WPIN
  (cd vendor/whisper.cpp && cmake -B build -DWHISPER_BUILD_TESTS=OFF -DGGML_NATIVE=OFF >/dev/null && cmake --build build -j"$(nproc)" --target whisper-cli >/dev/null)
fi

mkdir -p models
dl_model() { # file url sha256
  local f="models/$1"
  if [ ! -f "$f" ] || ! echo "$3  $f" | sha256sum -c --status 2>/dev/null; then
    curl -sL --retry 3 -o "$f" "$2"
    echo "$3  $f" | sha256sum -c --status
  fi
}
dl_model ggml-silero-v6.2.0.bin "https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin" 2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987

AMI90_LBL="hour-long compilation of 3 consecutive parts of one AMI day-session (ES2008 a+b+c, assembled parts, session gaps possible); real multi-speaker English meetings with overlap; overlap ordering inflates WER; diarization+notes not run"
MUCS_LBL="single-speaker code-switched Hindi-English tech lectures (MUCS 2021 sub-task2 test), concatenated utterances; NOT a multi-speaker Hinglish call; no free licensed real Hinglish multi-speaker corpus found"
FLEURS_LBL="read speech, single speaker, bounded 30-min test subset (FLEURS); jiwer lowercase+strip-punctuation normalization"
AMI_URL="https://groups.inf.ed.ac.uk/ami/corpus/"
MUCS_URL="https://openslr.org/104"
FLEURS_URL="https://huggingface.co/datasets/google/fleurs"

case "$LEG" in
  mucs60_small)
    dl_model ggml-small.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" 1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b
    AUDIO="$B/mucs/hinglish60.wav"; REF="$B/mucs/hinglish60_ref.txt"; MODEL=ggml-small.bin; LANG=auto; LBL="$MUCS_LBL"; URL=$MUCS_URL; LIC="CC BY-SA 4.0";;
  ami90_base)
    dl_model ggml-base.en.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002
    AUDIO="$B/ami/ES2008abc90.wav"; REF="$B/ami/ES2008abc90_ref.txt"; MODEL=ggml-base.en.bin; LANG=en; LBL="$AMI90_LBL"; URL=$AMI_URL; LIC="CC BY 4.0";;
  ami90_tiny)
    dl_model ggml-tiny.en.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin" 921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f
    AUDIO="$B/ami/ES2008abc90.wav"; REF="$B/ami/ES2008abc90_ref.txt"; MODEL=ggml-tiny.en.bin; LANG=en; LBL="$AMI90_LBL"; URL=$AMI_URL; LIC="CC BY 4.0";;
  fleurs_*30_small)
    dl_model ggml-small.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" 1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b
    L=$(echo "$LEG" | sed -E 's/fleurs_([a-z_]+)30_small/\1/')
    case "$L" in hi_in) SUF=" (Hindi)";; bn_in) SUF=" (Bengali - known unsupported, expect poor)";; ta_in) SUF=" (Tamil)";; es_419) SUF=" (Spanish)";; *) SUF="";; esac
    AUDIO="$B/fleurs/$L/${L}30.wav"; REF="$B/fleurs/$L/${L}30_ref.txt"; MODEL=ggml-small.bin; LANG=auto; LBL="$FLEURS_LBL$SUF"; URL=$FLEURS_URL; LIC="CC BY 4.0";;
  *) echo "unknown leg: $LEG" >&2; exit 2;;
esac

bash "$REPO/scripts/benchmark/setup_leg.sh" "$LEG" "$B" "$REPO"
python3 "$REPO/scripts/benchmark/run_one.py" "$AUDIO" "models/$MODEL" "$LANG" "$B/out_$LEG.json"
python3 "$REPO/scripts/benchmark/wer.py" "$B/out_$LEG.json" "$REF" "$LEG" "$LBL" "$URL" "$LIC"
J="$REPO/docs/benchmarks/2026-10-24-$LEG.json"
if grep -qiE 'AIza|SECRET|BEGIN .*PRIVATE KEY|ghp_' "$J"; then echo "SECRET-SCAN TRIP on $LEG - refusing artifact" >&2; exit 3; fi
echo "LEG OK: $LEG"
