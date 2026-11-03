# Hindi WER attribution probe (2026-11-04)

Why: hold-set WER for hi is high (67.4 CI / 68.5 Windows PC, 25.7-min
concat leg, ggml-small.bin, -l auto, -mc 0). Before calling that "quality",
we need to know how much is fixture/reference alignment vs recognition.

Method: fresh 30-clip slice of FLEURS hi_in test (public recordings,
CC BY 4.0), first 30 test rows, per-clip decode (NOT the concat harness),
whisper-cli built from v1.9.1 source on Linux 2-CPU, model
ggml-small.bin sha256 1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b
(from hf.co/ggerganov/whisper.cpp; the PC's file matches by byte SIZE
only - 487,601,967 - its hash was never captured, so exact identity with
the PC/CI model files is NOT established), silero v6.2.0 VAD, fixture
FLEURS hi_in test.tar.gz sha256
47c238b9cf7016ba596639bb3038b0c89dc6e85759f16d09c4f58c6dfa25c65f,
flags exactly the hold leg: `-l auto --vad -vmsd 10 -mc 0`.
WER metric: jiwer, lowercase+punct-stripped+whitespace-normalized, same as
scripts/benchmark/wer.py. Substitution classes from jiwer word alignments.
The classes below are a MANUAL/HEURISTIC assessment (NFKC + combining-mark
stripping, digit presence, Devanagari-range test) over one small slice -
method and uncertainty stated, not proven causal percentages. Per-clip
alignment dumps (ref/hyp pairs with classes) are kept out of the repo as
working artifacts.

Slice result: WER 63.1% (794 ref words; 335 hits, 404 substitutions,
55 deletions, 42 insertions, 0 UTF-8 replacements). Same range as the
concat legs; treat as representative of the same condition, not a
re-measurement (per-clip VAD/segmentation differs).

Substitution classes (404 total):
- different_word 267 (66%): genuine recognition divergence, mostly
  phonetically near (e.g. अस्थिर -> आज्तर, केंद्रक -> केंद्रख, कुछ -> अगो,
  यह -> यहां).
- script_mismatch 100 (24%): model emits Urdu/Arabic-script tokens
  (e.g. سے, سوانہ, پر) or Latin tokens (ph, ms) where the reference is
  Devanagari. Wrong-script emission is a real product defect for Hindi,
  not a scoring artifact.
- orthographic_variant 32 (7%): arguably equivalent spellings
  (समय/समये, हैं/है, प्लांट/प्लाँट, अक्सर/अकसर). Some are morphological
  (हैं/है), so not all are free.
- number_form 5 (1%): digits vs spelled-out (70 -> सद्टर is also a
  misrecognition of सत्तर; 11वीं -> गयारवी).

WER-point impact (794 ref words): normalization-ish artifacts
(orthographic + number form) = 37 errors = 4.7 points of the 63.1.
Script-mismatch = 100 errors = 12.6 points (real defect; a
transliteration-insensitive metric would hide it). Deletions (55) and
insertions (42) are real content words both ways.

Conclusions:
- The high hi WER is dominated by REAL recognition divergence (~66% of
  substitutions + all deletions/insertions), not fixture misalignment.
  Alignment/normalization accounts for at most ~5 WER points.
- A quarter of substitutions are wrong-script (Urdu/Latin) emissions - a
  distinct, fixable-looking failure mode worth its own probe (e.g. does a
  Devanagari-only constrained decode or a different model avoid it).
- Hypothesis, NOT established: model capacity (ggml-small is the only
  size benchmarked on hi). No larger-model comparison exists yet; naming
  capacity as the cause requires a ggml-medium/large leg on the same
  harness.
- Remaining unknowns: per-clip vs concat difference (~4-5 points vs the
  hold legs, unattributed); whether Urdu-script emissions correlate with
  specific speakers/clips; larger-model behavior.
