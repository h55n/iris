"""IRIS_WHISPER_EXTRA_FLAGS is appended after built-in defaults (benchmark
experiment configs), and FLEURS dev/hold splits stay disjoint from baseline."""
import subprocess
from iris import transcribe as T

def test_extra_flags_appended_after_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("IRIS_WHISPER_EXTRA_FLAGS", "-mc 0 --suppress-nst")
    import importlib
    importlib.reload(T)
    captured = {}
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        if "-oj" in cmd:
            open(cmd[cmd.index("-of") + 1] + ".json", "w").write('{"transcription":[]}')
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(T.subprocess, "run", fake_run)
    monkeypatch.setattr(T.os.path, "exists", lambda p: True)
    T.transcribe(str(tmp_path / "a.wav"), model=str(tmp_path / "m.bin"), language="ta")
    cmd = captured["cmd"]
    assert cmd[-3:] == ["-mc", "0", "--suppress-nst"]
    assert "-vmsd" in cmd  # built-in defaults preserved, extras come last
    monkeypatch.delenv("IRIS_WHISPER_EXTRA_FLAGS")
    importlib.reload(T)
