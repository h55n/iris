#!/bin/bash
# Downloads + builds the inputs for one benchmark leg into <bench_dir>.
# All inputs are re-downloaded from their original public sources; nothing
# corpus-derived is committed to git. Idempotent: existing files are reused.
set -euo pipefail
LEG=$1; B=${2:-/tmp/bench-ci}; REPO=$3
mkdir -p "$B"
AMI90_LBL_DUMMY=1
case "$LEG" in
  mucs60_small)
    mkdir -p "$B/mucs"; cd "$B/mucs"
    if [ ! -d test ]; then
      [ -f Hindi-English_test.tar.gz ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://www.openslr.org/resources/104/Hindi-English_test.tar.gz" Hindi-English_test.tar.gz gzip
      tar xzf Hindi-English_test.tar.gz && rm -f Hindi-English_test.tar.gz
    fi
    python3 "$REPO/scripts/benchmark/mucs_sample.py" test 60 hinglish60.wav hinglish60_ref.txt
    ;;
  ami90_base|ami90_tiny)
    bash "$REPO/scripts/benchmark/ami90_build.sh" "$B" "$REPO"
    ;;
  fleurs_*30_small)
    L=$(echo "$LEG" | sed -E 's/fleurs_([a-z_]+)30_small/\1/')
    mkdir -p "$B/fleurs/$L"; cd "$B/fleurs"
    [ -f "$L.test.tsv" ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$L/test.tsv" "$L.test.tsv" digit
    cd "$L"
    if [ ! -d test ]; then
      [ -f ../"$L.test.tar.gz" ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$L/audio/test.tar.gz" ../"$L.test.tar.gz" gzip
      tar xzf ../"$L.test.tar.gz" && rm -f ../"$L.test.tar.gz"
    fi
    python3 "$REPO/scripts/benchmark/fleurs_concat.py" "../$L.test.tsv" test 30 "${L}30.wav" "${L}30_ref.txt"
    ;;
  *) echo "unknown leg: $LEG" >&2; exit 2;;
esac
echo "setup done: $LEG"
