# Changelog

## 0.3.0 - 2026-10-21
- Rebrand to Iris complete, with backward compatibility: legacy X-Convo-Token
  and X-Convo-Title headers still accepted, legacy ~/.convo/key.txt still found.
- Local web UI: themes (6 accents x light/dark), iOS-feel motion, confetti on
  first save, search (/), rename, delete, raw markdown download, newer/older
  navigation, friendly locked-meeting page, real 404s.
- Security: sync /pull/ path traversal closed; ingest/sync servers validate
  Content-Length, since=, tokens and ids; titles HTML-escaped (XSS test).
- Integrity pass: generic owners (everyone/team/we) no longer demoted;
  invented names still caught.
- Voice enrollment: name + minimum-sample validation, corrupt voiceprints skipped.
- Android: JVM unit tests (13) for age decrypt, WAV header, meeting-app
  detection and key shape; key paste validated before sync.
- Robustness: corrupt meta.json can no longer crash the UI, list, sweep or sync;
  multi-part recordings never overwrite; sweep never deletes what it can't read.
- 132 Python tests + 13 Android JVM tests, both green on CI.

## 0.2.0 - 2026-10-21
- Diarization shipped (pyannote segmentation + ERes2Net via sherpa-onnx).
- Hindi/multilingual transcription via ggml-small with per-segment detection.
- Retention sweep, age encryption at rest, self-hosted sync relay, voiceprints.
