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
  mucs_dev_small|mucs_hold_small)
    # dev split: 15 min of utterances after the 60-min baseline; held-out: 30 min
    # after baseline+dev. Utterance-disjoint from baseline and each other.
    mkdir -p "$B/mucs"; cd "$B/mucs"
    if [ ! -d test ]; then
      [ -f Hindi-English_test.tar.gz ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://www.openslr.org/resources/104/Hindi-English_test.tar.gz" Hindi-English_test.tar.gz gzip
      tar xzf Hindi-English_test.tar.gz && rm -f Hindi-English_test.tar.gz
    fi
    if [ "$LEG" = mucs_dev_small ]; then
      python3 "$REPO/scripts/benchmark/mucs_sample.py" test 15 mucs_dev15.wav mucs_dev15_ref.txt 60
    else
      python3 "$REPO/scripts/benchmark/mucs_sample.py" test 30 mucs_hold30.wav mucs_hold30_ref.txt 60,15
    fi
    ;;
  ami90_base|ami90_tiny)
    bash "$REPO/scripts/benchmark/ami90_build.sh" "$B" "$REPO"
    ;;
  fleurs_*30_small)
    L=$(echo "$LEG" | sed -E 's/fleurs_(.+)30_small/\1/')
    mkdir -p "$B/fleurs/$L"; cd "$B/fleurs"
    [ -f "$L.test.tsv" ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$L/test.tsv" "$L.test.tsv" digit
    cd "$L"
    if [ ! -d test ]; then
      [ -f ../"$L.test.tar.gz" ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$L/audio/test.tar.gz" ../"$L.test.tar.gz" gzip
      tar xzf ../"$L.test.tar.gz" && rm -f ../"$L.test.tar.gz"
    fi
    python3 "$REPO/scripts/benchmark/fleurs_concat.py" "../$L.test.tsv" test 30 "${L}30.wav" "${L}30_ref.txt"
    ;;
  fleurs_dev_*_small|fleurs_hold_*_small|fleurs_dev_*_turbo|fleurs_hold_*_turbo)
    # dev split: utterances 30-45min of test.tsv; held-out split: 45-75min.
    # Both DISJOINT from the 2026-10-24 baseline (0-30min) and from each other.
    L=$(echo "$LEG" | sed -E 's/fleurs_(dev|hold)_(.+)_(small|turbo)/\2/')
    SPLIT=$(echo "$LEG" | sed -E 's/fleurs_(dev|hold)_(.+)_(small|turbo)/\1/')
    mkdir -p "$B/fleurs/$L"; cd "$B/fleurs"
    [ -f "$L.test.tsv" ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$L/test.tsv" "$L.test.tsv" digit
    cd "$L"
    if [ ! -d test ]; then
      [ -f ../"$L.test.tar.gz" ] || bash "$REPO/scripts/benchmark/dl_verified.sh" "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$L/audio/test.tar.gz" ../"$L.test.tar.gz" gzip
      tar xzf ../"$L.test.tar.gz" && rm -f ../"$L.test.tar.gz"
    fi
    if [ "$SPLIT" = dev ]; then
      python3 "$REPO/scripts/benchmark/fleurs_concat.py" "../$L.test.tsv" test 15 "${L}_dev15.wav" "${L}_dev15_ref.txt" 30
    else
      python3 "$REPO/scripts/benchmark/fleurs_concat.py" "../$L.test.tsv" test 30 "${L}_hold30.wav" "${L}_hold30_ref.txt" 30,15
    fi
    ;;
  *) echo "unknown leg: $LEG" >&2; exit 2;;
esac
echo "setup done: $LEG"
