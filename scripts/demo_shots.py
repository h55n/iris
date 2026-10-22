"""Build a throwaway demo store and take screenshots of the web UI at
1440/1024/390 wide, light and dark. Usage: python3 scripts/demo_shots.py OUTDIR
Needs playwright and a Chrome/Chromium (set CHROME to override the path)."""
import os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iris import library as L, store as S

OUT = sys.argv[1] if len(sys.argv) > 1 else "screenshots"
STORE, PORT = "/tmp/iris-demo-shots-store", 18499
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")

TRANSCRIPT = """[00:14] Speaker 1: We shipped the Android recorder on Friday. Manual toggle only.
[00:23] Priya: I will own the sync server. It only moves transcripts and notes, never audio.
[00:31] Speaker 1: We also decided recordings delete themselves after seven days.
"""
NOTES = """## Summary
Standup on the recorder app. Android shipped, sync server has an owner, audio stays local.

## Decisions
- Recordings delete themselves after seven days.
  > "We also decided recordings delete themselves after seven days." [00:31]

## Action items
- [ ] Own the sync server, moving only transcripts and notes. (Priya)
  > "I will own the sync server. It only moves transcripts and notes, never audio." [00:23]
"""

def build():
    shutil.rmtree(STORE, ignore_errors=True); os.makedirs(STORE)
    f = L.create_folder(STORE, "Product")
    mid = S.new_meeting(STORE, "Weekly standup")
    S.write_text(STORE, mid, "transcript.md", TRANSCRIPT)
    S.write_text(STORE, mid, "notes.md", NOTES)
    L.move(STORE, mid, f["id"]); L.set_pinned(STORE, mid, True)
    L.new_note(STORE, "Launch checklist", folder=f["id"])
    L.new_note(STORE, "Reading list")
    return mid, f["id"]

def main():
    from playwright.sync_api import sync_playwright
    mid, fid = build(); os.makedirs(OUT, exist_ok=True)
    srv = subprocess.Popen([sys.executable, "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    pages = {"home": "/", "note": f"/meeting/{mid}", "folder": f"/folder/{fid}", "ask": "/ask", "trash": "/trash"}
    bad = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
            for scheme in ("light", "dark"):
                for w, h in ((1440, 900), (1024, 768), (390, 844)):
                    pg = b.new_page(viewport={"width": w, "height": h}, color_scheme=scheme)
                    errs = []
                    pg.on("pageerror", lambda e: errs.append(str(e)))
                    for name, path in pages.items():
                        pg.goto(f"http://127.0.0.1:{PORT}{path}"); pg.wait_for_timeout(1900)
                        over = pg.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                        if over: bad.append(f"{name} {w} {scheme}: horizontal overflow")
                        pg.screenshot(path=f"{OUT}/{name}_{w}_{scheme}.png")
                    bad += [f"{w} {scheme}: {e}" for e in errs]
                    pg.close()
            b.close()
    finally:
        srv.kill()
    print("problems:", bad or "none")

if __name__ == "__main__":
    main()
