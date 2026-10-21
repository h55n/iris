"""Real Chrome: drag folders and pinned notes, order sticks after reload."""
import os, subprocess, time, json
import pytest
pw = pytest.importorskip("playwright.sync_api")
CHROME = "/usr/bin/google-chrome"
pytestmark = pytest.mark.skipif(not os.path.exists(CHROME), reason="needs Chrome")
STORE, PORT = "/tmp/iris-reorder-browser", 18491

def test_drag_folder_and_pinned_note_order_persists():
    import sys; sys.path.insert(0, ".")
    from iris import library as L
    os.system(f"rm -rf {STORE}"); os.makedirs(STORE)
    fa, fb = L.create_folder(STORE, "Alpha")["id"], L.create_folder(STORE, "Beta")["id"]
    n1, n2 = L.new_note(STORE, "First"), L.new_note(STORE, "Second")
    time.sleep(1.1)
    for n in (n1, n2): L.set_pinned(STORE, n, True)
    srv = subprocess.Popen(["python3", "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
            pg = b.new_page(viewport={"width": 1440, "height": 900}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{PORT}/")
            names = lambda: pg.eval_on_selector_all(".folder[data-fid]", "els=>els.map(e=>e.textContent.replace(/[0-9▾▸]/g,'').trim())")
            assert names() == ["Alpha", "Beta"]
            pg.drag_and_drop(f'[data-fid="{fb}"]', f'[data-fid="{fa}"]')
            pg.wait_for_load_state("load"); time.sleep(0.5)
            assert names() == ["Beta", "Alpha"]
            pinned = lambda: pg.eval_on_selector_all('[data-group="pinned"] .nav-title', "els=>els.map(e=>e.textContent)")
            before = pinned()
            first, second = before[0], before[1]
            pg.drag_and_drop(f'[data-group="pinned"][data-mid="{n2 if second == "Second" else n1}"]',
                             f'[data-group="pinned"][data-mid="{n1 if first == "First" else n2}"]')
            pg.wait_for_load_state("load"); time.sleep(0.5)
            assert pinned() == [second, first]
            pg.reload()
            assert names() == ["Beta", "Alpha"] and pinned() == [second, first]
            assert errs == []
            b.close()
    finally:
        srv.kill()
