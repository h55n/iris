"""Watch daemon: runs meeting auto-detection and nudges the user when a
meeting starts. DETECTION ONLY - it never starts recording by itself.
Linux desktop notification via notify-send; other platforms: prints.

  python3 iris/watch.py            # watch, notify on meeting start/end
"""
import subprocess, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iris.detect import Detector

def notify(title: str, body: str) -> str:
    """Desktop notification; returns what was shown (for tests/logs)."""
    msg = f"{title}: {body}"
    try:
        subprocess.run(["notify-send", "-a", "Iris", title, body],
                       capture_output=True, timeout=5)
    except Exception:
        pass  # headless / no notify-send: stdout already covers it
    print(msg, flush=True)
    return msg

def format_event(event: dict) -> tuple[str, str]:
    if event["type"] == "meeting_start":
        return (f"Meeting detected: {event['app']}",
                "Tap to record: python3 iris/record.py (recording is always manual)")
    return (f"Meeting ended: {event.get('app', '')}",
            "If you recorded, run: python3 iris/cli.py ingest <file>")

def main():
    d = Detector()
    print("watching for meetings (Zoom/Meet/Teams/Webex)... Ctrl-C to stop", flush=True)
    d.run(on_event=lambda e: notify(*format_event(e)))

if __name__ == "__main__":
    main()
