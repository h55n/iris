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
