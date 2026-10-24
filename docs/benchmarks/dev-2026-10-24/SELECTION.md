# Dev selection and held-out plan (frozen 2026-10-25 ~01:05 IST, before any held-out run)

## Selected config (candidate A)
ggml-small.bin + IRIS_WHISPER_EXTRA_FLAGS="-mc 0" (no context carry between
windows). Product-compatible: flags only, no model/cost change. No shipped
default is changed by this document.

## Split provenance (untouched until now)
- FLEURS baseline: test.tsv utterances 0-30min (committed 9e3cea4, frozen).
- FLEURS dev: utterances 30-45min (fleurs_concat.py arg6=30), text-disjoint
  from baseline (verified intersections = 0); used for all tuning above.
- FLEURS held-out: utterances 45-75min (arg6=30,15), text-disjoint from both;
  speaker overlap unverifiable (FLEURS tsv has no speaker IDs) - within-corpus
  validation. Never run before this plan.
- MUCS baseline: first 60min of segments order. Dev: next 15min (skip 60).
  Held-out: next 30min (skip 60,15). Utterance-disjoint (verified).
- AMI-90: no splits; the "-mc 0" check was a same-input toggle vs the frozen
  baseline input (28.6/39.3 -> 28.3/36.5).

## Dev evidence for the selection (single runs, observed differences,
## uncertainty unestimated; dev slices; full table in this directory)
- ta_in: base 81.3 -> selected 75.5. hi_in: base 72.7 -> selected 74.1
  (observed worsening, carried into confirmation). es_419: 6.6 -> 5.9.
  mucs: 81.2 -> 78.7. ami90 same-input: 28.6/39.3 -> 28.3/36.5.
  bn_in: ~100 under all tested configs including large-v3-turbo.
- Rejected alternative: large-v3-turbo + "-mc 0" showed hi 52.6 but mucs 97.0;
  the turbo MUCS hypothesis is Arabic-script-dominant (6147 Arabic + 1311
  Latin chars, 0 Devanagari) vs small's Devanagari-dominant output - a
  script/language-selection mismatch observation under lang=auto, not an
  established causal mechanism and not an excuse for the poorer end-to-end
  score. es turbo 6.9 vs small 5.9. ~2x CI compute.

## Held-out confirmation (one run set, not a tuning surface)
Legs fleurs_hold_{ta_in,hi_in,bn_in,es_419}_small + mucs_hold_small, run
paired: flags="" vs flags="-mc 0" on the same held-out inputs. Report paired
baseline/selected results per leg including regressions and failures.
