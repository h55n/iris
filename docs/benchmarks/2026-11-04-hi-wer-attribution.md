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

## Same-slice config comparison: explicit `-l hi` vs `-l auto` (ggml-small.bin)

Identical 30-clip FLEURS hi_in test slice, identical decode flags
(--vad silero v6.2.0 -vmsd 10 -mc 0 -oj, whisper.cpp v1.9.1,
ggml-small.bin sha256 1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b).
Per-clip alignment dumps: alignments-small-auto.json, alignments-small-hi.json.

| config | WER | hits | subs | del | ins | utf8-repl chars |
|---|---|---|---|---|---|---|
| small + `-l auto` | 63.1% | 335 | 404 | 55 | 42 | 0 |
| small + `-l hi` | 57.6% | 391 | 346 | 57 | 54 | 1 |

Substitution classes (manual/heuristic categories, method unchanged):

| class | auto | hi |
|---|---|---|
| different_word | 267 (66%) | 301 (87%) |
| script_mismatch | 100 (24%) | 2 (<1%) |
| orthographic_variant | 32 (7%) | 38 (11%) |
| number_form | 5 (1%) | 5 (1%) |

Grounded finding: on this slice, explicit `-l hi` collapses the wrong-script
emission mode (100 -> 2 substitution pairs) and lowers WER by 5.5 points. This
is consistent with auto language-ID sometimes selecting Urdu (Arabic script) or
emitting Latin tokens; the model itself produces Devanagari when the language
is pinned. The residual error mass stays in within-Devanagari different_word
substitutions.

Not a winner declaration: one 30-clip slice, per-clip decode, insertions are
slightly higher with `-l hi` (42 -> 54), the code-switching (Hinglish) cost of
pinning the language is untested here, and the classes are heuristic. The
existing benchmark baseline (auto, hold-2026-10-25) is unchanged.

## ggml-medium leg: blocked by sandbox memory (not a model result)

Attempted ggml-medium.bin (sha256
6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208) on the same
slice in this sandbox: 6/6 attempted clips were SIGKILLed by the OOM killer.
The box has 1982 MB RAM; whisper-cli reached ~1.8 GB RSS during model load/
decode before being killed, so zero medium JSONs were produced. This is an
environmental limit, not evidence about medium's quality. Options to complete
the capacity comparison: run on a machine with >=4 GB free RAM (e.g. the user's
PC, needs owner permission), or a quantized medium build (a different artifact
than the pinned hash; would be labeled separately and confounds capacity with
quantization).
