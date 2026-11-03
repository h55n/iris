"""iris ingest --language / --careful wiring: forced-language ingest picks the
multilingual model, Bengali is refused at the flag, and conflicts are caught."""
import sys
import pytest
from iris import cli

def _run_cli(monkeypatch, tmp_path, argv, capture):
    audio = tmp_path / "m.wav"; audio.write_bytes(b"RIFF")
    monkeypatch.setattr(sys, "argv", ["iris"] + [a if a != "{audio}" else str(audio) for a in argv])
    monkeypatch.setattr(cli, "cmd_ingest", lambda *a, **kw: capture.update(args=a, kwargs=kw))
    cli.main(None)

def test_language_and_careful_reach_ingest(monkeypatch, tmp_path):
    cap = {}
    _run_cli(monkeypatch, tmp_path, ["ingest", "{audio}", "--language", "hi", "--careful"], cap)
    assert cap["kwargs"]["language"] == "hi"
    assert cap["kwargs"]["careful"] is True
    assert cap["kwargs"]["multilingual"] is False

def test_default_language_english_careful_off(monkeypatch, tmp_path):
    cap = {}
    _run_cli(monkeypatch, tmp_path, ["ingest", "{audio}"], cap)
    assert cap["kwargs"]["language"] == "en"
    assert cap["kwargs"]["careful"] is False

def test_bengali_refused_at_flag(monkeypatch, tmp_path, capsys):
    cap = {}
    with pytest.raises(SystemExit) as e:
        _run_cli(monkeypatch, tmp_path, ["ingest", "{audio}", "--language", "bn"], cap)
    assert e.value.code == 1
    assert "not supported" in capsys.readouterr().err
    assert cap == {}  # ingest never ran

def test_language_multilingual_conflict(monkeypatch, tmp_path, capsys):
    cap = {}
    with pytest.raises(SystemExit) as e:
        _run_cli(monkeypatch, tmp_path, ["ingest", "{audio}", "--language", "hi", "--multilingual"], cap)
    assert e.value.code == 1
    assert "conflict" in capsys.readouterr().err
    assert cap == {}

def test_bad_language_code(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        _run_cli(monkeypatch, tmp_path, ["ingest", "{audio}", "--language", "hindi!"], {})
    assert e.value.code == 1
    assert "bad --language" in capsys.readouterr().err

def test_forced_hindi_uses_multilingual_model(monkeypatch, tmp_path):
    """cmd_ingest with language=hi must not use the English-only default model."""
    from iris import transcribe as T
    seen = {}
    monkeypatch.setattr(cli, "STORE", str(tmp_path))
    (tmp_path / "m1").mkdir()
    (tmp_path / "m1" / "meta.json").write_text("{}")
    monkeypatch.setattr(cli.store, "new_meeting", lambda s, t: "m1")
    monkeypatch.setattr(cli.store, "attach_audio", lambda s, m, a: None)
    monkeypatch.setattr(T, "transcribe", lambda audio, **kw: seen.update(kw) or [])
    monkeypatch.setattr(T, "transcript_markdown", lambda segs: "t")
    monkeypatch.setattr(cli.store, "write_text", lambda *a, **kw: None)
    class _B:
        name = "fake"
        def notes(self, t): return {"integrity": {"passed": 0, "checked": 0}}
    monkeypatch.setattr(cli.backends, "get_backend", lambda name: _B())
    monkeypatch.setattr(cli.verify, "verify_notes", lambda n, s: n)
    monkeypatch.setattr(cli.render, "render_notes", lambda *a: "n")
    monkeypatch.setattr(cli.json, "dump", lambda *a, **kw: None)
    monkeypatch.setattr(cli.os.path, "exists", lambda p: False)
    import iris.cloud as CL
    monkeypatch.setattr(CL, "auto_sync", lambda s: None)
    monkeypatch.setenv("IRIS_WHISPER_MULTILINGUAL_MODEL", "models/ggml-small.bin")
    cli.cmd_ingest(str(tmp_path / "m.wav"), language="hi", careful=True)
    assert seen["model"] == "models/ggml-small.bin"   # not the .en default
    assert seen["language"] == "hi"
    assert seen["careful"] is True
