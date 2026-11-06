import iris.detect as D

class Fake(Detector := D.Detector):
    def __init__(self, procs=None, titles=None, mic=False, **kw):
        super().__init__(poll_seconds=0, confirm_ticks=2, end_after_ticks=2, **kw)
        self._procs, self._titles, self._mic = procs or [], titles or [], mic
    def running_processes(self): return self._procs
    def window_titles(self): return self._titles
    def mic_in_use(self): return self._mic

def test_zoom_process_fires_after_confirm_ticks():
    d = Fake(procs=["zoom", "python3"])
    assert d.tick()["event"] is None          # tick 1: not yet confirmed
    e = d.tick()["event"]                     # tick 2
    assert e and e["type"] == "meeting_start" and e["app"] == "Zoom"

def test_no_duplicate_start_while_running():
    d = Fake(procs=["zoom"])
    d.tick(); d.tick()
    assert d.in_meeting
    assert d.tick()["event"] is None

def test_end_after_silence():
    d = Fake(procs=["zoom"])
    d.tick(); d.tick()
    d._procs = []
    d.tick()
    e = d.tick()["event"]
    assert e and e["type"] == "meeting_end"

def test_browser_window_title_meet():
    d = Fake(procs=["firefox"], titles=["Meet - abc-defg-hij - Mozilla Firefox"])
    d.tick(); e = d.tick()["event"]
    assert e and e["app"] == "Google Meet"

def test_random_process_ignored():
    d = Fake(procs=["spotify", "code"], titles=["Spotify - song"])
    assert d.tick()["event"] is None and d.tick()["event"] is None

def test_mic_signal_added_only_with_meeting_app():
    d = Fake(procs=["teams"], mic=True)
    s = d.tick()
    assert any(x["source"] == "mic" for x in s["signals"])
    d2 = Fake(procs=["spotify"], mic=True)
    assert not any(x["source"] == "mic" for x in d2.tick()["signals"])

def test_transient_glitch_does_not_fire():
    d = Fake(procs=["zoom"])
    d.tick()
    d._procs = []          # one glitchy poll
    d.tick(); d.tick()
    assert not d.in_meeting

def test_discord_process_detected():
    d = Fake(procs=["discord"])
    d.tick(); e = d.tick()["event"]
    assert e and "Discord" in e["app"]

def test_jitsi_window_title():
    d = Fake(procs=["firefox"], titles=["Daily standup | meet.jit.si - Firefox"])
    d.tick(); e = d.tick()["event"]
    assert e and "Jitsi" in e["app"]

def test_whereby_window_title():
    d = Fake(procs=["chrome"], titles=["Whereby - room/chat"])
    d.tick(); e = d.tick()["event"]
    assert e and "Whereby" in e["app"]


def test_windows_tasklist_csv(monkeypatch):
    import subprocess
    monkeypatch.setattr(D.platform, 'system', lambda: 'Windows')
    calls = []
    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0,
            '"Zoom.exe","123","Console","1","23,456 K"\r\n'
            '"ms-teams.exe","456","Console","1","12,000 K"\r\n', '')
    monkeypatch.setattr(D.subprocess, 'run', run)
    assert D.Detector().running_processes() == ['Zoom.exe', 'ms-teams.exe']
    assert calls[0][0] == ['tasklist', '/FO', 'CSV', '/NH']
    assert calls[0][1]['timeout'] == 10
    assert calls[0][1]['errors'] == 'replace'


def test_windows_failed_probe_ignores_stdout(monkeypatch):
    import subprocess
    monkeypatch.setattr(D.platform, 'system', lambda: 'Windows')
    monkeypatch.setattr(D.subprocess, 'run', lambda cmd, **kw:
        subprocess.CompletedProcess(cmd, 1, '"Zoom.exe","123"', 'access denied'))
    assert D.Detector().running_processes() == []


def test_windows_probe_timeout_is_nonfatal(monkeypatch):
    import subprocess
    monkeypatch.setattr(D.platform, 'system', lambda: 'Windows')
    def fail(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 10)
    monkeypatch.setattr(D.subprocess, 'run', fail)
    assert D.Detector().running_processes() == []


def test_native_executable_names_are_case_insensitive():
    d = Fake(procs=['ZOOM.EXE', 'ms-teams.exe', 'CiscoCollabHost.exe'])
    apps = {s.app for s in d.sense() if s.source == 'process'}
    assert apps == {'Zoom', 'Microsoft Teams', 'Webex'}


def test_executable_matching_is_exact_not_substring():
    d = Fake(procs=['myzoom.exe', 'teams-helper.exe', 'not-discord.exe'])
    assert d.sense() == []


def test_windows_does_not_probe_linux_mic_or_x11(monkeypatch):
    monkeypatch.setattr(D.platform, 'system', lambda: 'Windows')
    monkeypatch.setenv('DISPLAY', ':0')
    calls = []
    def unexpected(*args, **kwargs):
        calls.append(args)
        raise AssertionError('Linux probe must not run on Windows')
    monkeypatch.setattr(D.subprocess, 'run', unexpected)
    d = D.Detector()
    assert d.mic_in_use() is False
    assert d.window_titles() == []
    assert calls == []


def test_posix_process_probe_keeps_command(monkeypatch):
    import subprocess
    monkeypatch.setattr(D.platform, 'system', lambda: 'Linux')
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, 'zoom\n teams\n\n', '')
    monkeypatch.setattr(D.subprocess, 'run', run)
    assert D.Detector().running_processes() == ['zoom', 'teams']
    assert calls == [['ps', '-eo', 'comm=']]


def test_native_windows_tasklist_detects_real_executable(tmp_path):
    import platform
    import shutil
    import subprocess
    import sys
    import time
    import pytest
    if platform.system() != 'Windows':
        pytest.skip('real tasklist integration requires Windows')
    # A renamed Python process, not Zoom: no meeting, devices or network access.
    executable = tmp_path / 'Zoom.exe'
    shutil.copy2(sys.executable, executable)
    import os
    env = dict(os.environ, PYTHONHOME=sys.base_prefix)
    child = subprocess.Popen([str(executable), '-c', 'import time; time.sleep(30)'], env=env)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            assert child.poll() is None, 'renamed process exited before probe'
            signals = D.Detector().sense()
            if any(s.source == 'process' and s.app == 'Zoom' for s in signals):
                break
            time.sleep(0.2)
        else:
            pytest.fail('real tasklist did not detect the running Zoom.exe fixture')
    finally:
        child.terminate()
        child.wait(timeout=10)
