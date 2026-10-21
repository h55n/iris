"""End-to-end pipeline test: ingest -> store -> verify -> render -> encrypt,
with whisper and the notes backend stubbed (they're covered by live tests)."""
import os, json, subprocess
from iris import cli, store, crypto as C

SEGMENTS = [
    {"start": 0.0, "end": 3.0, "text": "Decision: we ship the recorder on Friday."},
    {"start": 3.5, "end": 7.0, "text": "Priya will own the sync server."},
]
NOTES = {
    "summary": "Short sync.",
    "decisions": [{"text": "Ship Friday", "evidence": "we ship the recorder on Friday", "at": "00:00"}],
    "action_items": [{"text": "Own sync server", "owner": "Priya",
                      "evidence": "Priya will own the sync server", "at": "00:03"}],
}

class StubBackend:
    name = "stub"
    def notes(self, tmd): return dict(NOTES)

def test_full_ingest_pipeline(tmp_path, monkeypatch):
    store_dir = str(tmp_path / "store")
    key = str(tmp_path / "key.txt")
    monkeypatch.setattr(cli, "STORE", store_dir)
    monkeypatch.setattr(cli.T, "transcribe", lambda a: list(SEGMENTS))
    monkeypatch.setattr(cli.backends, "get_backend", lambda name: StubBackend())
    monkeypatch.setattr(C, "DEFAULT_KEY", key)
    monkeypatch.setattr("iris.store.C.DEFAULT_KEY", key)
    C.generate_key(key)

    wav = tmp_path / "m.wav"; wav.write_bytes(b"RIFF" + b"\0" * 2000)
    cli.cmd_ingest(str(wav), "stub")

    mids = os.listdir(store_dir)
    assert len(mids) == 1
    d = os.path.join(store_dir, mids[0])
    # encrypted at rest, plaintext gone
    assert not os.path.exists(os.path.join(d, "notes.md"))
    assert os.path.exists(os.path.join(d, "notes.md.age"))
    # roundtrip: verified notes with receipts render back correctly
    texts = store.decrypt_meeting(store_dir, mids[0], key)
    assert "Ship Friday" in texts["notes.md"]
    assert "2/2 claims verified" in texts["notes.md"]
    assert "[00:00]" in texts["transcript.md"]
    # meta records integrity
    meta = json.load(open(os.path.join(d, "meta.json")))
    assert meta["integrity"] == {"checked": 2, "passed": 2}
    assert meta["encrypted"] is True

def test_verifier_demotes_invented_claim_in_pipeline(tmp_path, monkeypatch):
    store_dir = str(tmp_path / "store")
    key = str(tmp_path / "key.txt")
    monkeypatch.setattr(cli, "STORE", store_dir)
    monkeypatch.setattr(cli.T, "transcribe", lambda a: list(SEGMENTS))
    bad = dict(NOTES); bad["action_items"] = [
        {"text": "Buy servers", "owner": "Alex", "evidence": "Alex will buy servers", "at": "00:05"}]
    class Bad:
        name = "stub"
        def notes(self, tmd): return bad
    monkeypatch.setattr(cli.backends, "get_backend", lambda name: Bad())
    monkeypatch.setattr(C, "DEFAULT_KEY", key)
    monkeypatch.setattr("iris.store.C.DEFAULT_KEY", key)
    if not os.path.exists(key): C.generate_key(key)

    wav = tmp_path / "m.wav"; wav.write_bytes(b"RIFF" + b"\0" * 2000)
    cli.cmd_ingest(str(wav), "stub")
    mid = os.listdir(store_dir)[0]
    notes = store.decrypt_meeting(store_dir, mid, key)["notes.md"]
    assert "Buy servers" in notes and "Unverified" in notes   # demoted, not deleted
    assert "- [ ] Buy servers" not in notes.split("Unverified")[0]  # not in the trusted list

def test_transcript_markdown_speaker_numbering():
    from iris import transcribe as T
    md = T.transcript_markdown([{"start": 0, "text": "hi", "speaker": 0},
                                {"start": 61.2, "text": "yo", "speaker": 1}])
    lines = md.splitlines()
    assert lines[0] == "[00:00] Speaker 1: hi"
    assert lines[1] == "[01:01] Speaker 2: yo"

def test_transcript_markdown_custom_names_and_lang():
    from iris import transcribe as T
    md = T.transcript_markdown(
        [{"start": 5, "text": "namaste", "speaker": 2, "lang": "hi"}],
        speaker_names={2: "Hassan"})
    assert md == "[00:05] Hassan: <hi> namaste"

def test_transcript_markdown_no_speaker_no_lang():
    from iris import transcribe as T
    md = T.transcript_markdown([{"start": 0, "text": "plain"}])
    assert md == "[00:00] plain"

def test_mmss_rolls_past_an_hour_as_minutes():
    from iris import transcribe as T
    # long meetings stay MM:SS (61:01), matching the evidence quotes in notes
    assert T.mmss(3661.7) == "61:01"
    assert T.mmss(0) == "00:00"
    assert T.mmss(59.94) == "00:59"

def test_transcribe_missing_model_named():
    from iris import transcribe as T
    import pytest
    with pytest.raises(FileNotFoundError, match="whisper model not found"):
        T.transcribe("/tmp/whatever.wav", model="/tmp/no-such-model.bin")

def test_to_wav16k_missing_input_named():
    from iris import transcribe as T
    import pytest
    with pytest.raises(FileNotFoundError, match="audio not found"):
        T.to_wav16k("/tmp/definitely-not-here.mp3")

def test_to_wav16k_unreadable_media_named():
    from iris import transcribe as T
    import pytest, tempfile
    junk = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    junk.write(b"this is not audio"); junk.close()
    with pytest.raises(RuntimeError, match="ffmpeg could not convert"):
        T.to_wav16k(junk.name)
