"""Real Chrome with a fake microphone: record in the page, stop, upload, and the audio lands on the server."""
import os, subprocess, sys, time
import pytest
pw = pytest.importorskip("playwright.sync_api")
CHROME = "/usr/bin/google-chrome"
pytestmark = pytest.mark.skipif(not os.path.exists(CHROME), reason="needs Chrome")
STORE, PORT = "/tmp/iris-pwa-browser", 18498

def test_browser_records_and_uploads():
    os.system(f"rm -rf {STORE}"); os.makedirs(STORE)
    srv = subprocess.Popen([sys.executable, "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
            ctx = b.new_context(permissions=["microphone"])
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}/record")
            pg.fill("#rtitle", "Browser test")
            pg.click("#rbtn"); pg.wait_for_timeout(2500)
            assert "Stop" in pg.inner_text("#rbtn")
            pg.click("#rbtn")
            # transcription may fail on machines without whisper; either way the audio must be saved
            deadline = time.time() + 30
            while time.time() < deadline:
                if any(os.path.exists(os.path.join(STORE, m, f)) for m in os.listdir(STORE)
                       if os.path.isdir(os.path.join(STORE, m)) for f in ("audio.webm", "audio.ogg", "audio.mp4")): break
                time.sleep(0.5)
            b.close()
        mids = [m for m in os.listdir(STORE) if os.path.isdir(os.path.join(STORE, m))]
        assert mids and any(f.startswith("audio.") for f in os.listdir(os.path.join(STORE, mids[0])))
    finally:
        srv.kill()
