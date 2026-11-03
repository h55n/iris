"""Phone-declared transcription settings: header parsing on the ingest server
and language routing in the pipeline. Without this the phone path silently ran
the English model on Hindi/Hinglish recordings (base.en translates/drops Hindi,
tested Oct 21). Defaults must equal the pre-header behavior."""
import json, os, urllib.request, urllib.error
from iris import pipeline, transcribe as T
from iris.ingest_server import _transcription_opts

# ---- header parsing (pure) ----

def test_defaults_match_pre_header_behavior():
    opts, err = _transcription_opts({})
    assert err is None
    assert opts == {"language": "en", "multilingual": False, "careful": False,
                    "allow_unsupported": False}

def test_hindi_and_careful_parsed():
    opts, err = _transcription_opts({"X-Iris-Language": "hi", "X-Iris-Careful": "1"})
    assert err is None
    assert opts["language"] == "hi" and opts["careful"] is True

def test_multilingual_flag_parsed():
    opts, err = _transcription_opts({"X-Iris-Multilingual": "1"})
    assert err is None and opts["multilingual"] is True and opts["language"] == "en"

def test_language_and_multilingual_conflict():
    opts, err = _transcription_opts({"X-Iris-Language": "hi", "X-Iris-Multilingual": "1"})
    assert opts is None and "conflict" in err

def test_bad_language_code_rejected():
    opts, err = _transcription_opts({"X-Iris-Language": "hindi!"})
    assert opts is None and "bad X-Iris-Language" in err

def test_bengali_refused_without_override():
    opts, err = _transcription_opts({"X-Iris-Language": "bn"})
    assert opts is None and "not supported" in err and "Allow-Unsupported" in err

def test_bengali_allowed_with_override_header():
    opts, err = _transcription_opts({"X-Iris-Language": "bn", "X-Iris-Allow-Unsupported": "1"})
    assert err is None and opts["language"] == "bn" and opts["allow_unsupported"] is True

# ---- pipeline routing (mocked whisper) ----

def _fake_pipeline(monkeypatch, tmp_path):
    """pipeline.py imports its deps locally, so patch the source modules."""
    import iris.store as S, iris.backends as BK, iris.verify as VF, iris.render as RN, iris.crypto as CR
    seen = {}
    monkeypatch.setattr(S, "new_meeting", lambda s, t: "m1")
    monkeypatch.setattr(S, "write_text", lambda *a, **kw: None)
    monkeypatch.setattr(S, "encrypt_meeting", lambda *a: [])
    (tmp_path / "m1").mkdir()
    (tmp_path / "m1" / "meta.json").write_text("{}")
    monkeypatch.setattr(T, "transcribe",
                        lambda audio, **kw: seen.setdefault("transcribe", kw) or [])
    monkeypatch.setattr(T, "transcribe_multilingual",
                        lambda audio, **kw: seen.setdefault("multi", kw) or [])
    monkeypatch.setattr(T, "transcript_markdown", lambda segs: "t")
    class _B:
        name = "fake"
        def notes(self, t): return {"integrity": {"passed": 0, "checked": 0}}
    monkeypatch.setattr(BK, "get_backend", lambda n: _B())
    monkeypatch.setattr(VF, "verify_notes", lambda n, s: n)
    monkeypatch.setattr(RN, "render_notes", lambda *a: "n")
    monkeypatch.setattr(CR, "DEFAULT_KEY", "/nonexistent")
    return seen

def test_pipeline_default_english_unchanged(monkeypatch, tmp_path):
    seen = _fake_pipeline(monkeypatch, tmp_path)
    out = pipeline.process_audio(str(tmp_path), b"x" * 2000)
    assert "transcribe" in seen and "multi" not in seen
    assert seen["transcribe"].get("careful") is False
    assert out["meeting"] == "m1"

def test_pipeline_hindi_routes_to_multilingual_model(monkeypatch, tmp_path):
    seen = _fake_pipeline(monkeypatch, tmp_path)
    monkeypatch.setenv("IRIS_WHISPER_MULTILINGUAL_MODEL", "models/ggml-small.bin")
    pipeline.process_audio(str(tmp_path), b"x" * 2000, language="hi", careful=True)
    assert seen["transcribe"]["model"] == "models/ggml-small.bin"
    assert seen["transcribe"]["language"] == "hi"
    assert seen["transcribe"]["careful"] is True

def test_pipeline_multilingual_path(monkeypatch, tmp_path):
    seen = _fake_pipeline(monkeypatch, tmp_path)
    pipeline.process_audio(str(tmp_path), b"x" * 2000, multilingual=True, careful=True)
    assert "multi" in seen and "transcribe" not in seen
    assert seen["multi"]["careful"] is True

def test_pipeline_meta_records_transcription_provenance(monkeypatch, tmp_path):
    dumped = {}
    seen = _fake_pipeline(monkeypatch, tmp_path)
    monkeypatch.setattr("iris.pipeline.json.dump",
                        lambda obj, f, **kw: dumped.update(obj) if isinstance(obj, dict) else None)
    pipeline.process_audio(str(tmp_path), b"x" * 2000, language="hi", careful=True)
    assert dumped.get("transcription") == {"language": "hi", "multilingual": False, "careful": True}

# ---- live server: guard rails reject before whisper is needed ----

import subprocess, time
STORE2 = "/tmp/iris-ingest-store-lang"
PORT2 = 18473

import pytest
@pytest.fixture(scope="module", autouse=True)
def lang_server():
    os.system(f"rm -rf {STORE2}")
    os.makedirs(STORE2)
    srv = subprocess.Popen(["python3", "iris/ingest_server.py", "--store", STORE2,
                            "--token", "t0ken", "--port", str(PORT2)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    yield
    srv.kill()

def _post_lang(headers):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT2}/ingest", data=b"x" * 2000, method="POST")
    req.add_header("X-Iris-Token", "t0ken")
    for k, v in headers.items(): req.add_header(k, v)
    try:
        r = urllib.request.urlopen(req)
        return r.getcode(), json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def test_live_bengali_rejected_400(lang_server):
    code, body = _post_lang({"X-Iris-Language": "bn"})
    assert code == 400 and "not supported" in body["error"]

def test_live_bad_language_400(lang_server):
    code, body = _post_lang({"X-Iris-Language": "h4"})
    assert code == 400 and "bad X-Iris-Language" in body["error"]

def test_live_conflict_400(lang_server):
    code, body = _post_lang({"X-Iris-Language": "hi", "X-Iris-Multilingual": "1"})
    assert code == 400 and "conflict" in body["error"]
