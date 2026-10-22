"""Real Chrome: the saved-meeting plant animates, and reduced motion turns it off."""
import os, subprocess, time, sys
import pytest
pw = pytest.importorskip("playwright.sync_api")
CHROME = "/usr/bin/google-chrome"
pytestmark = pytest.mark.skipif(not os.path.exists(CHROME), reason="needs Chrome")
STORE, PORT = "/tmp/iris-motion-browser", 18492

def test_plant_animates_and_reduced_motion_disables():
    sys.path.insert(0, ".")
    from iris import library as L
    os.system(f"rm -rf {STORE}"); os.makedirs(STORE)
    mid = L.new_note(STORE, "Fresh")
    srv = subprocess.Popen(["python3", "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    q = "[...document.querySelectorAll('.mascot, .mascot .stem path, .mascot .leaf, .mascot .bloom')].map(e=>getComputedStyle(e).animationName)"
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}/meeting/{mid}")
            names = pg.evaluate(q)
            assert names[0] == "settle" and "draw" in names and "unfurl" in names and names[-1] == "pop"
            pg2 = b.new_page(reduced_motion="reduce")
            pg2.goto(f"http://127.0.0.1:{PORT}/meeting/{mid}")
            assert set(pg2.evaluate(q)) == {"none"}
            b.close()
    finally:
        srv.kill()
