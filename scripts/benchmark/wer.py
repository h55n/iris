#!/usr/bin/env python3
# WER for one leg: jiwer full-transcript, two normalizations:
#   wer                                   lowercase + punctuation stripped + whitespace normalized (standard ASR normalization)
#   wer_lowercase_only_punct_counted      lowercase only; punctuation mismatches count as errors
# Appends a metrics JSON (no raw corpus transcripts) to docs/benchmarks/ and prints one line.
import sys, json, os, datetime, wave, contextlib, jiwer
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
result_json, ref_txt, leg, label, source_url, license_ = sys.argv[1:7]
d = json.load(open(result_json))
hyp = " ".join(s["text"] for s in d["segs"])
ref = open(ref_txt, encoding="utf-8").read()
tr = jiwer.Compose([jiwer.ToLowerCase(), jiwer.RemovePunctuation(),
                    jiwer.RemoveMultipleSpaces(), jiwer.Strip(), jiwer.ReduceToListOfListOfWords()])
m = jiwer.process_words(ref, hyp, reference_transform=tr, hypothesis_transform=tr)
tr_lc = jiwer.Compose([jiwer.ToLowerCase(), jiwer.ReduceToListOfListOfWords()])
m_lc = jiwer.process_words(ref, hyp, reference_transform=tr_lc, hypothesis_transform=tr_lc)
with contextlib.closing(wave.open(d["audio"])) as w:
    dur_min = round(w.getnframes() / w.getframerate() / 60, 1)
metrics = {
  "leg": leg, "label": label, "source_url": source_url, "license": license_,
  "date": datetime.date.today().isoformat(),
  "audio_minutes": dur_min, "model": os.path.basename(d["model"]), "language_arg": d["language"],
  "wall_s": d["wall_s"], "peak_child_mb": d["peak_child_mb"], "segments": d["segments"],
  "utf8_replacements": d.get("utf8_replacements", 0),
  "wer": round(m.wer * 100, 1), "wer_lowercase_only_punct_counted": round(m_lc.wer * 100, 1),
  "mer": round(m.mer * 100, 1), "wil": round(m.wil * 100, 1), "hits": m.hits,
  "substitutions": m.substitutions, "deletions": m.deletions, "insertions": m.insertions,
  "wer_method": "primary 'wer': jiwer full-transcript, lowercase + punctuation stripped + whitespace normalized (standard ASR normalization). 'wer_lowercase_only_punct_counted': lowercase only, punctuation mismatches count as errors - comparable to the 2026-10-24 morning AMI-a figures (37.9/42.9).",
  "engine": "iris.transcribe (repo product path, whisper-cli + silero VAD)",
  "measured_on": os.environ.get("MEASURED_ON", "sandbox (2 CPU, 2GB RAM)"),
}
out = os.path.join(REPO, "docs", "benchmarks", f"2026-10-24-{leg}.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(metrics, open(out, "w"), indent=1)
print(f"WER {leg}: {metrics['wer']}%  ({dur_min}min, {os.path.basename(d['model'])}, {d['wall_s']}s, peak {d['peak_child_mb']}MB) -> {out}", flush=True)
