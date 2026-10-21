"""Real Chrome: slash menu, Ctrl+B, list continuation, autosave."""
import os, subprocess, time, json
import pytest
pw = pytest.importorskip("playwright.sync_api")
CHROME = "/usr/bin/google-chrome"
pytestmark = pytest.mark.skipif(not os.path.exists(CHROME), reason="needs Chrome")
STORE, PORT = "/tmp/iris-editor-browser", 18490

@pytest.fixture(scope="module")
def page():
    os.system(f"rm -rf {STORE}"); os.makedirs(STORE)
    srv = subprocess.Popen(["python3", "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = b.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/")
        pg.click("text=+ New note"); pg.wait_for_url("**/meeting/*")
        pg.errs = errs
        yield pg
        b.close()
    srv.kill()

def notes_on_disk(pg):
    mid = pg.url.split("/")[-1]
    return open(f"{STORE}/{mid}/notes.md").read()

def test_slash_menu_inserts_heading(page):
    page.click("#ed")
    page.keyboard.type("/head")
    assert page.is_visible("#slash")
    page.keyboard.press("ArrowDown"); page.keyboard.press("Enter")   # Heading 2
    page.keyboard.type("Plan")
    assert page.input_value("#ed") == "## Plan"
    assert not page.is_visible("#slash")

def test_slash_menu_escape_keeps_text(page):
    page.keyboard.press("Enter"); page.keyboard.type("/to")
    assert page.is_visible("#slash")
    page.keyboard.press("Escape")
    assert not page.is_visible("#slash") and page.input_value("#ed").endswith("/to")

def test_ctrl_b_and_i_wrap_selection(page):
    page.fill("#ed", "ship plants")
    page.evaluate("var e=document.getElementById('ed');e.setSelectionRange(0,4)")
    page.keyboard.press("Control+b")
    assert page.input_value("#ed") == "**ship** plants"
    page.keyboard.press("Control+b")
    assert page.input_value("#ed") == "ship plants"
    page.keyboard.press("Control+i")
    assert page.input_value("#ed") == "*ship* plants"

def test_list_continues_and_exits(page):
    page.fill("#ed", "")
    page.keyboard.type("- one\ntwo\n\nplain")
    assert page.input_value("#ed") == "- one\n- two\nplain"

def test_autosave_reaches_disk_and_no_js_errors(page):
    page.fill("#ed", "")
    page.keyboard.type("saved **bold**")
    time.sleep(1.0)
    assert notes_on_disk(page) == "saved **bold**"
    assert page.errs == []
