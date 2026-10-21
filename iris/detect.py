"""Meeting auto-detection daemon (laptop).

Detects that a meeting is happening WITHOUT joining it or reading its
content, then emits an event so the user can start recording with one tap.
Detection only. Recording stays manual-confirmed (see README: consent).

Signals, best to weakest:
  1. A meeting app's native process is running (zoom, teams, webex, ...).
  2. A capture (mic) stream is active while a meeting app is up.
  3. A browser window title mentions a meeting URL (meet.google.com etc.)
     - only available on X11; Wayland hides titles, documented in TESTED.md.

Phone reality (honest): Android can neither see another app's mic nor read
its audio (Play policy May 2022 + OS). On Android we detect only the
foreground app name (if the user grants Usage Access) and show a
"meeting? tap to record" notification. iOS: not possible at all.
"""
from __future__ import annotations
import json, os, re, subprocess, time
from dataclasses import dataclass, field

MEETING_PROCESSES = {
    "zoom": "Zoom",
    "zoom.us": "Zoom",
    "teams": "Microsoft Teams",
    "ms-teams": "Microsoft Teams",
    "webex": "Webex",
    "CiscoCollabHost": "Webex",
    "skype": "Skype",
    "slack": "Slack (huddle?)",
    "discord": "Discord (call?)",
    "jitsi-meet": "Jitsi Meet",
    "zoho meeting": "Zoho Meeting",
}
MEETING_URL_PATTERNS = [
    (re.compile(r"meet\.google\.com", re.I), "Google Meet"),
    # Meet window titles show the code, not the URL: "Meet - abc-defg-hij"
    (re.compile(r"(?:^|\s)Meet - [a-z]{3}-[a-z]{4}-[a-z]{3}(?:\s|$)", re.I), "Google Meet"),
    (re.compile(r"teams\.microsoft\.com|teams\.live\.com", re.I), "Microsoft Teams (web)"),
    (re.compile(r"zoom\.us/(j|wc)/", re.I), "Zoom (web)"),
    (re.compile(r"\.webex\.com/(meet|join)", re.I), "Webex (web)"),
    (re.compile(r"meet\.jit\.si", re.I), "Jitsi Meet (web)"),
    # Whereby titles show "Whereby - room", not the URL
    (re.compile(r"whereby\.com/|Whereby - ", re.I), "Whereby (web)"),
    (re.compile(r"discord\.com/channels", re.I), "Discord (web)"),
]

@dataclass
class Signal:
    source: str          # process | mic | window
    app: str
    detail: str = ""

@dataclass
class Detector:
    """Polls probes; fires on_meeting_start once per meeting (debounced)."""
    poll_seconds: float = 5.0
    confirm_ticks: int = 2          # signal must persist this many polls
    end_after_ticks: int = 6        # this many silent polls = meeting over
    _streak: int = 0
    _silent: int = 0
    in_meeting: bool = False
    meeting_app: str = ""
    events: list = field(default_factory=list)

    # ---- probes (overridable for tests / non-Linux) ----
    def running_processes(self) -> list[str]:
        try:
            out = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=10).stdout
        except Exception:
            return []
        return [l.strip() for l in out.splitlines() if l.strip()]

    def mic_in_use(self) -> bool:
        # Linux: any open capture PCM device outside our own process.
        try:
            out = subprocess.run(["fuser", "/dev/snd/pcmC0D0c"], capture_output=True, text=True, timeout=5)
            return bool(out.stdout.strip())
        except Exception:
            return False

    def window_titles(self) -> list[str]:
        # X11 only; Wayland returns [] by design (no protocol for foreign titles).
        if not os.environ.get("DISPLAY"):
            return []
        try:
            out = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", ".", "getwindowname", "%@"],
                                 capture_output=True, text=True, timeout=10).stdout
            return [l for l in out.splitlines() if l]
        except Exception:
            return []

    # ---- detection ----
    def sense(self) -> list[Signal]:
        sigs = []
        procs = set(self.running_processes())
        for p in procs:
            if p in MEETING_PROCESSES:
                sigs.append(Signal("process", MEETING_PROCESSES[p], p))
        titles = self.window_titles()
        for t in titles:
            for pat, app in MEETING_URL_PATTERNS:
                if pat.search(t):
                    sigs.append(Signal("window", app, t[:80]))
        if sigs and self.mic_in_use():
            sigs.append(Signal("mic", sigs[0].app, "capture stream active"))
        return sigs

    def tick(self) -> dict:
        sigs = self.sense()
        event = None
        if sigs:
            self._silent = 0
            self._streak += 1
            if not self.in_meeting and self._streak >= self.confirm_ticks:
                self.in_meeting = True
                self.meeting_app = sigs[0].app
                event = {"type": "meeting_start", "app": self.meeting_app,
                         "signals": [s.__dict__ for s in sigs]}
        else:
            self._streak = 0
            if self.in_meeting:
                self._silent += 1
                if self._silent >= self.end_after_ticks:
                    self.in_meeting = False
                    event = {"type": "meeting_end", "app": self.meeting_app}
        if event:
            self.events.append(event)
        return {"in_meeting": self.in_meeting, "app": self.meeting_app,
                "signals": [s.__dict__ for s in sigs], "event": event}

    def run(self, on_event=None, max_ticks=None):
        n = 0
        while max_ticks is None or n < max_ticks:
            state = self.tick()
            if state["event"] and on_event:
                on_event(state["event"])
            n += 1
            time.sleep(self.poll_seconds)

if __name__ == "__main__":
    d = Detector()
    print(json.dumps(d.tick(), indent=1))
