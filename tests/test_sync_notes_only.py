import json, os, tempfile
from iris import sync as S


def _store():
    d = tempfile.mkdtemp()
    m = os.path.join(d, "m1"); os.makedirs(m)
    json.dump({"id": "m1", "title": "T", "audio_files": ["audio.wav"]}, open(os.path.join(m, "meta.json"), "w"))
    open(os.path.join(m, "notes.md"), "w").write("# T\n- decided")
    open(os.path.join(m, "transcript.md"), "w").write("[00:00] private words")
    open(os.path.join(m, "audio.wav"), "wb").write(b"RIFF")
    return d


def test_notes_only_bundle_has_no_transcript_or_audio():
    d = _store()
    full = S._bundle(d, "m1")
    lean = S._bundle(d, "m1", notes_only=True)
    assert "transcript" in full and "transcript" not in lean
    assert lean["notes"].startswith("# T")
    assert "audio" not in lean and "RIFF" not in json.dumps(lean)


def test_notes_only_changes_hash_and_pushes_lean_payload(monkeypatch):
    d = _store()
    assert S.bundle_hash(d, "m1") != S.bundle_hash(d, "m1", notes_only=True)
    sent = []
    monkeypatch.setattr(S, "_req", lambda url, tok, payload=None: sent.append((url, payload)) or {})
    S.push_changed(d, "https://x.test/sync", "tok", notes_only=True)
    url, payload = sent[0]
    assert url.endswith("/sync/push/m1") and "transcript" not in payload and "notes" in payload
