import os, sys, time, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iris import verify, store, transcribe as T

SEGS = [
    {"start": 0.0, "end": 4.0, "text": "Let's ship the Android recorder on Friday."},
    {"start": 5.0, "end": 9.0, "text": "Priya will own the sync server."},
    {"start": 10.0, "end": 14.0, "text": "We decided transcripts stay local only."},
]

def test_verify_honest_notes_pass():
    notes = {"summary": "s",
             "decisions": [{"text": "Transcripts stay local", "evidence": "transcripts stay local only", "at": "00:10"}],
             "action_items": [{"text": "Priya owns sync", "owner": "Priya", "evidence": "Priya will own the sync server", "at": "00:05"}]}
    out = verify.verify_notes(notes, SEGS)
    assert out["integrity"] == {"checked": 2, "passed": 2}, out["integrity"]
    assert not out["unverified_decisions"] and not out["unverified_action_items"]

def test_verify_catches_fabrication():
    notes = {"summary": "s",
             "decisions": [{"text": "Ship Monday", "evidence": "we will ship on Monday", "at": "00:01"}],
             "action_items": [{"text": "Arun does QA", "owner": "Arun", "evidence": "Arun agreed to run QA", "at": "00:11"}]}
    out = verify.verify_notes(notes, SEGS)
    assert out["integrity"]["passed"] == 0 and out["integrity"]["checked"] == 2
    assert len(out["unverified_decisions"]) == 1 and len(out["unverified_action_items"]) == 1
    assert out["unverified_action_items"][0]["unverified_reason"] == "evidence not found verbatim in transcript"

def test_verify_bad_timestamp():
    notes = {"summary": "s", "decisions": [], "action_items": [
        {"text": "x", "evidence": "transcripts stay local only", "at": "59:59"}]}
    out = verify.verify_notes(notes, SEGS)
    assert out["unverified_action_items"][0]["unverified_reason"] == "timestamp outside transcript"

def test_verify_catches_invented_owner():
    notes = {"summary": "s", "decisions": [], "action_items": [
        {"text": "Own sync", "owner": "Sam", "evidence": "Priya will own the sync server", "at": "00:05"}]}
    out = verify.verify_notes(notes, SEGS)
    assert out["unverified_action_items"][0]["unverified_reason"] == "owner not mentioned in transcript"
    notes2 = {"summary": "s", "decisions": [], "action_items": [
        {"text": "Own sync", "owner": "Priya", "evidence": "Priya will own the sync server", "at": "00:05"}]}
    out2 = verify.verify_notes(notes2, SEGS)
    assert out2["integrity"]["passed"] == 1

def test_retention_sweep():
    d = tempfile.mkdtemp()
    mid = store.new_meeting(d, "old meeting")
    audio = os.path.join(d, "in.wav"); open(audio, "w").write("RIFFfake")
    store.attach_audio(d, mid, audio)
    store.write_text(d, mid, "transcript.md", "[00:00] hello")
    meta_p = os.path.join(d, mid, "meta.json")
    meta = json.load(open(meta_p)); meta["created"] = time.time() - 8 * 86400
    json.dump(meta, open(meta_p, "w"))
    deleted = store.sweep(d)
    assert len(deleted) == 1 and not os.path.exists(deleted[0])
    assert os.path.exists(os.path.join(d, mid, "transcript.md"))  # transcript survives
    mid2 = store.new_meeting(d, "fresh")
    audio2 = os.path.join(d, "in2.wav"); open(audio2, "w").write("RIFFfake")
    store.attach_audio(d, mid2, audio2)
    assert store.sweep(d) == []  # fresh recordings kept
    shutil.rmtree(d)

def test_mmss():
    assert T.mmss(65) == "01:05" and T.mmss(0) == "00:00"

def test_sync_roundtrip_and_no_audio():
    import threading
    from http.server import HTTPServer
    from iris import sync_server, sync
    root = tempfile.mkdtemp(); srv_dir = tempfile.mkdtemp()
    httpd = HTTPServer(("127.0.0.1", 0), sync_server.make_handler(srv_dir, "tok"))
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    server = f"http://127.0.0.1:{port}"
    mid = store.new_meeting(root, "sync test")
    audio = os.path.join(root, "a.wav"); open(audio, "w").write("RIFFfake")
    store.attach_audio(root, mid, audio)
    store.write_text(root, mid, "transcript.md", "[00:00] hello")
    store.write_text(root, mid, "notes.md", "# notes")
    r = sync.push(root, mid, server, "tok")
    assert r["ok"]
    assert not os.path.exists(os.path.join(srv_dir, mid, "audio.wav"))
    dev2 = tempfile.mkdtemp()
    got = sync.pull_all(dev2, server, "tok")
    assert got == [mid]
    assert open(os.path.join(dev2, mid, "transcript.md")).read() == "[00:00] hello"
    assert not os.path.exists(os.path.join(dev2, mid, "audio.wav"))
    try:
        sync.push(root, mid, server, "wrong"); assert False
    except Exception: pass
    httpd.shutdown()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"PASS {fn.__name__}")
    print(f"{len(fns)}/{len(fns)} tests pass")

def test_transcript_markdown_lang_tags():
    from iris import transcribe as T
    segs = [
        {"start": 0.0, "text": "hello there", "lang": "en"},
        {"start": 61.0, "text": "हिन्दी पंक्ति", "lang": "hi"},
        {"start": 65.0, "text": "no lang key"},
    ]
    md = T.transcript_markdown(segs)
    lines = md.splitlines()
    assert "<hi>" in lines[1] and lines[1].startswith("[01:01]")
    assert "<hi>" not in lines[0] and "<hi>" not in lines[2]

def test_transcript_markdown_speaker_names():
    from iris import transcribe as T
    segs = [{"start": 5.0, "text": "hi", "speaker": 0, "lang": "en"}]
    md = T.transcript_markdown(segs, speaker_names={0: "Priya"})
    assert "Priya:" in md and "Speaker 1" not in md

def test_ollama_unreachable_error_is_actionable():
    from iris import backends as B
    be = B.OllamaBackend(base="http://127.0.0.1:9")  # nothing listens on port 9
    import pytest
    with pytest.raises(RuntimeError, match="ollama serve"):
        be.notes("[00:01] hello")

def test_ultramarine_without_key_is_actionable():
    from iris import backends as B
    import pytest
    with pytest.raises(RuntimeError, match="IRIS_ULTRAMARINE_KEY"):
        B.UltramarineBackend(key="").notes("[00:01] hi")

def test_parse_notes_malformed_json_named():
    from iris import backends as B
    import pytest
    with pytest.raises(RuntimeError, match="malformed JSON"):
        B._parse_notes("sure! here are your notes: ...")

def test_parse_notes_fills_missing_keys():
    from iris import backends as B
    n = B._parse_notes('{"summary": "short"}')
    assert n["decisions"] == [] and n["action_items"] == []

def test_parse_notes_fenced_json():
    from iris import backends as B
    n = B._parse_notes('```json\n{"summary": "s", "decisions": [], "action_items": []}\n```')
    assert n["summary"] == "s"
