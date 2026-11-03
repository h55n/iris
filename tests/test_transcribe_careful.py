"""--careful / IRIS_WHISPER_CAREFUL ships the measured -mc 0 decode ONLY where
held-out evidence shows a win (hi, ta, multilingual auto - TESTED.md 2026-10-25).
Spanish/English keep the standard decode (es regressed +0.6, en neutral).
Bengali is refused loudly: wrong script, measured 100% WER, do not return garbage."""
import subprocess, sys
import pytest
from iris import transcribe as T

MAIN_FIXTURE = '{"transcription":[{"offsets":{"from":0,"to":2000},"text":"hello"}]}'

def _patch(monkeypatch, tmp_path, extra_flags=""):
    captured = {"cmds": []}
    def fake_run(cmd, **kw):
        captured["cmds"].append(cmd)
        if "-oj" in cmd:
            open(cmd[cmd.index("-of") + 1] + ".json", "w").write(MAIN_FIXTURE)
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(T.subprocess, "run", fake_run)
    monkeypatch.setattr(T.os.path, "exists", lambda p: True)
    monkeypatch.setattr(T, "EXTRA_FLAGS", extra_flags)
    monkeypatch.delenv("IRIS_WHISPER_CAREFUL", raising=False)
    return captured

def _whisper_cmds(captured):
    return [c for c in captured["cmds"] if "-oj" in c]

def test_careful_hindi_gets_mc0(monkeypatch, tmp_path):
    c = _patch(monkeypatch, tmp_path)
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="hi", careful=True)
    cmd = _whisper_cmds(c)[0]
    assert cmd[-2:] == T.CAREFUL_FLAGS == ["-mc", "0"]

def test_careful_tamil_gets_mc0(monkeypatch, tmp_path):
    c = _patch(monkeypatch, tmp_path)
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="ta", careful=True)
    assert _whisper_cmds(c)[0][-2:] == ["-mc", "0"]

def test_careful_auto_multilingual_gets_mc0(monkeypatch, tmp_path):
    c = _patch(monkeypatch, tmp_path)
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="auto", careful=True)
    assert _whisper_cmds(c)[0][-2:] == ["-mc", "0"]

def test_careful_spanish_not_applied_with_note(monkeypatch, tmp_path, capsys):
    c = _patch(monkeypatch, tmp_path)
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="es", careful=True)
    assert "-mc" not in _whisper_cmds(c)[0]
    assert "no measured win" in capsys.readouterr().err

def test_careful_english_not_applied(monkeypatch, tmp_path):
    c = _patch(monkeypatch, tmp_path)
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="en", careful=True)
    assert "-mc" not in _whisper_cmds(c)[0]

def test_env_var_enables_careful(monkeypatch, tmp_path):
    c = _patch(monkeypatch, tmp_path)
    monkeypatch.setenv("IRIS_WHISPER_CAREFUL", "1")
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="hi")
    assert _whisper_cmds(c)[0][-2:] == ["-mc", "0"]

def test_default_decode_unchanged(monkeypatch, tmp_path):
    """No flag, no env: Hindi still uses the standard decode (default untouched)."""
    c = _patch(monkeypatch, tmp_path)
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="hi")
    assert "-mc" not in _whisper_cmds(c)[0]

def test_careful_not_duplicated_when_extra_flags_already_carry_it(monkeypatch, tmp_path):
    c = _patch(monkeypatch, tmp_path, extra_flags="-mc 0")
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="hi", careful=True)
    assert _whisper_cmds(c)[0].count("-mc") == 1

def test_bengali_refused(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    with pytest.raises(T.UnsupportedLanguageError, match="wrong script"):
        T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="bn")

def test_bengali_refused_even_with_careful(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    with pytest.raises(T.UnsupportedLanguageError):
        T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="bn", careful=True)

def test_multilingual_bengali_detection_warns(monkeypatch, tmp_path, capsys):
    """If per-segment detection finds Bengali speech, warn that the transcript is unreliable."""
    captured = {"n": 0}
    def fake_run(cmd, **kw):
        if "-oj" in cmd:
            captured["n"] += 1
            body = MAIN_FIXTURE if captured["n"] == 1 else \
                '{"transcription":[{"offsets":{"from":0,"to":2000},"text":"x"}],"result":{"language":"bn"}}'
            open(cmd[cmd.index("-of") + 1] + ".json", "w").write(body)
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(T.subprocess, "run", fake_run)
    monkeypatch.setattr(T.os.path, "exists", lambda p: True)
    monkeypatch.delenv("IRIS_WHISPER_CAREFUL", raising=False)
    segs = T.transcribe_multilingual(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"))
    assert segs[0]["lang"] == "bn"
    assert "UNSUPPORTED" in capsys.readouterr().err

def test_multilingual_careful_reaches_main_pass(monkeypatch, tmp_path):
    captured = {"n": 0, "cmds": []}
    def fake_run(cmd, **kw):
        captured["cmds"].append(cmd)
        if "-oj" in cmd:
            captured["n"] += 1
            body = MAIN_FIXTURE if captured["n"] == 1 else \
                '{"transcription":[{"offsets":{"from":0,"to":2000},"text":"x"}],"result":{"language":"hi"}}'
            open(cmd[cmd.index("-of") + 1] + ".json", "w").write(body)
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(T.subprocess, "run", fake_run)
    monkeypatch.setattr(T.os.path, "exists", lambda p: True)
    monkeypatch.delenv("IRIS_WHISPER_CAREFUL", raising=False)
    T.transcribe_multilingual(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), careful=True)
    main_pass = [c for c in captured["cmds"] if "-oj" in c and "-ss" not in c][0]
    assert main_pass[-2:] == ["-mc", "0"]
