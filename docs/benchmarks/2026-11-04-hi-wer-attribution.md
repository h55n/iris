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
- Capacity hypothesis now tested on this slice (medium legs below):
  medium reduces different_word substitutions (267 -> 171 with auto) and
  overall WER (-11.3 points) but does NOT remove wrong-script emissions -
  script_mismatch grows to 157 with medium+auto, and only language
  pinning collapses it (157 -> 1 with medium+hi).
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

## ggml-medium leg: blocked by sandbox memory (not a model result) (superseded: completed on the PC)

The sandbox attempt (1982 MB RAM) OOM-killed 6/6 clips at ~1.8 GB RSS, so the
leg ran on the user's Windows PC instead (i7-13700HX, 15.7 GB RAM, authorized
scope, public fixtures only). whisper.cpp v1.9.1 binary
(whisper-bin-x64/Release), ggml-medium.bin downloaded from the same pinned HF
URL, sha256 re-verified on the PC:
6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208
(size 1,533,763,059 B). Identical 30-clip slice, identical decode flags
(-l auto --vad -vmsd 10 -mc 0). Per-clip times 24-146.5 s; leg 05:23-05:47 IST
2026-11-04. Outputs persist on the PC: D:\iris-test\wer-attr\out-med\
(30 whisper JSONs), alignments-med-auto.json (per-clip alignment dump),
analysis-med-auto.json (summary), D:\iris-test\medleg.log (timings).

medium + `-l hi` leg: same PC, same model file, identical slice and flags
except `-l hi`. Per-clip times 23.8-187.9 s; leg completed 06:21 IST
2026-11-04. Outputs persist on the PC: D:\iris-test\wer-attr\out-med-hi\
(30 whisper JSONs), alignments-med-hi.json (per-clip alignment dump),
analysis-med-hi.json (summary), D:\iris-test\medleghi.log (timings).

## Full same-slice comparison (FLEURS hi_in, 30 clips, per-clip decode)

| config | WER | hits | subs | del | ins | utf8-repl |
|---|---|---|---|---|---|---|
| small + `-l auto` | 63.1% | 335 | 404 | 55 | 42 | 0 |
| small + `-l hi` | 57.6% | 391 | 346 | 57 | 54 | 1 |
| medium + `-l auto` | 51.8% | 409 | 369 | 16 | 26 | 0 |
| medium + `-l hi` | 39.8% | 514 | 267 | 13 | 36 | 0 |

Substitution classes (manual/heuristic categories, method unchanged):

| class | small+auto | small+hi | medium+auto | medium+hi |
|---|---|---|---|---|
| different_word | 267 (66%) | 301 (87%) | 171 (46%) | 214 (80%) |
| script_mismatch | 100 (24%) | 2 (<1%) | 157 (43%) | 1 (<1%) |
| orthographic_variant | 32 (7%) | 38 (11%) | 37 (10%) | 49 (18%) |
| number_form | 5 (1%) | 5 (1%) | 4 (1%) | 3 (1%) |

Grounded reading on this slice: model capacity (small -> medium) reduces
genuine misrecognition (different_word 267 -> 171, deletions 55 -> 16, WER
-11.3 points) but does NOT remove the wrong-script mode - script_mismatch grows
to 157 (43% of remaining substitutions). Pinning the language remains the only
observed lever that removes wrong-script emissions (100 -> 2 with
small+hi, 157 -> 1 with medium+hi).
The two levers are orthogonal here. Still not a winner declaration: one
30-clip read-speech slice, per-clip decode, heuristic classes, Hinglish
code-switching cost of language pinning untested, and the existing auto
baseline (hold-2026-10-25) is unchanged.
