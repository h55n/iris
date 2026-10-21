"""Live web UI: new note, edit, pin, folders over real HTTP."""
import json, os, subprocess, time, urllib.request, urllib.parse
import pytest

STORE = "/tmp/iris-webui-lib-store"
PORT = 18474
BASE = f"http://127.0.0.1:{PORT}"

@pytest.fixture(scope="module", autouse=True)
def server():
    os.system(f"rm -rf {STORE}"); os.makedirs(STORE)
    srv = subprocess.Popen(["python3", "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    yield
    srv.kill()

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None

def post(path, data):
    req = urllib.request.Request(BASE + path, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        r = urllib.request.build_opener(_NoRedirect).open(req)
        return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")

def get(path): return urllib.request.urlopen(BASE + path).read().decode()

def test_new_note_then_edit_saves_text():
    st, loc = post("/new", {})
    assert st == 303 and loc.startswith("/meeting/")
    mid = loc.split("/")[-1]
    st, _ = post(f"/notes/{mid}", {"text": "## Decisions\n- plants win"})
    assert st == 204
    assert open(os.path.join(STORE, mid, "notes.md")).read() == "## Decisions\n- plants win"
    assert "plants win" in get(loc)

def test_pin_and_unpin():
    mid = post("/new", {"title": "Pin me"})[1].split("/")[-1]
    post(f"/pin/{mid}", {})
    assert json.load(open(os.path.join(STORE, mid, "meta.json"))).get("pinned") is True
    post(f"/unpin/{mid}", {})
    assert "pinned" not in json.load(open(os.path.join(STORE, mid, "meta.json")))

def test_folder_lifecycle_and_move():
    st, loc = post("/folders/new", {"name": "Project Alpha"})
    assert st == 303 and loc.startswith("/folder/")
    fid = loc.split("/")[-1]
    mid = post("/new", {"folder": fid})[1].split("/")[-1]
    assert json.load(open(os.path.join(STORE, mid, "meta.json")))["folder"] == fid
    post(f"/folders/{fid}/rename", {"name": "Alpha 2"})
    assert "Alpha 2" in get("/")
    post(f"/move/{mid}", {"folder": ""})
    assert "folder" not in json.load(open(os.path.join(STORE, mid, "meta.json")))
    post(f"/folders/{fid}/delete", {})
    assert "Alpha 2" not in get("/") and os.path.isdir(os.path.join(STORE, mid))

def test_bad_ids_rejected():
    assert post("/notes/..%2Fetc", {"text": "x"})[0] == 404
    assert post("/pin/nope", {})[0] == 404

def test_inline_scripts_are_valid_js():
    import re, subprocess, tempfile
    mid = post("/new", {})[1].split("/")[-1]
    html = get(f"/meeting/{mid}")
    for i, sc in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
        f = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False); f.write(sc); f.close()
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        assert r.returncode == 0, f"script {i}: {r.stderr[:200]}"

def test_palette_and_fonts_are_notion_granola():
    html = get("/")
    assert "--accent:#3f8f4f" in html            # Granola-style green default
    assert "ui-sans-serif" in html and "BlinkMacSystemFont" in html
    assert 'data-t="blue"' in html               # old blue stays as a theme

def test_mobile_menu_toggle_present():
    html = get("/")
    assert 'id=navtoggle' in html and 'class=menubtn' in html

def test_home_lists_recent_notes_with_preview_and_pinned_first():
    mid = post("/new", {"title": "Home preview note"})[1].split("/")[-1]
    post(f"/notes/{mid}", {"text": "# Heading line\nbody"})
    post(f"/pin/{mid}", {})
    html = get("/")
    assert "Home preview note" in html and "body" in html
    recent = html.split("<div class=recent>", 1)[1]
    assert recent.index(">Pinned<") < recent.index("Home preview note")

def test_preview_skips_headings():
    mid = post("/new", {"title": "Preview skip"})[1].split("/")[-1]
    post(f"/notes/{mid}", {"text": "## Summary\nThe real first sentence"})
    assert "The real first sentence" in get("/")

def test_speaker_rename_over_http():
    mid = post("/new", {"title": "Call"})[1].split("/")[-1]
    open(os.path.join(STORE, mid, "transcript.md"), "w").write("[00:01] Speaker 2: hello there\n[00:04] Speaker 1: hi")
    req = urllib.request.Request(BASE + f"/speaker/{mid}", method="POST",
        data=urllib.parse.urlencode({"old": "Speaker 2", "new": "Priya Sharma"}).encode())
    assert json.load(urllib.request.urlopen(req))["changed"] == 1
    html = get(f"/meeting/{mid}")
    assert 'data-spk="Priya Sharma"' in html and "hello there" in html
    bad = urllib.request.Request(BASE + f"/speaker/{mid}", method="POST",
        data=urllib.parse.urlencode({"old": "Speaker 1", "new": "<b>"}).encode())
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(bad)
    assert e.value.code == 400

def test_transcript_chip_for_devanagari_name():
    mid = post("/new", {"title": "Hindi"})[1].split("/")[-1]
    open(os.path.join(STORE, mid, "transcript.md"), "w").write("[00:01] प्रिया: नमस्ते")
    assert 'data-spk="प्रिया"' in get(f"/meeting/{mid}")

def test_language_tags_render_as_pills_not_raw_markup():
    mid = post("/new", {"title": "Mixed"})[1].split("/")[-1]
    open(os.path.join(STORE, mid, "transcript.md"), "w").write("[00:01] Speaker 1: <hinglish> kal meeting hai kya")
    html = get(f"/meeting/{mid}")
    assert 'class="lang lang-hinglish">hinglish</span>' in html and "&lt;hinglish&gt;" not in html

def test_ask_hides_language_tags():
    from iris import ask as A
    mid = post("/new", {"title": "AskTag"})[1].split("/")[-1]
    open(os.path.join(STORE, mid, "transcript.md"), "w").write("[00:01] Speaker 1: <hinglish> kal planning meeting hai kya")
    hit = A.ask(STORE, "planning meeting kal")[0]
    assert hit["quote"] == "Speaker 1: kal planning meeting hai kya"

def test_delete_goes_to_trash_and_can_be_restored():
    mid = post("/new", {"title": "Trash me"})[1].split("/")[-1]
    post(f"/delete/{mid}", {})
    assert not os.path.isdir(os.path.join(STORE, mid))
    assert f"/restore/{mid}" in get("/trash") and f"/meeting/{mid}" not in get("/")
    post(f"/restore/{mid}", {})
    assert os.path.isdir(os.path.join(STORE, mid)) and f"/restore/{mid}" not in get("/trash")

def test_empty_trash_is_permanent():
    mid = post("/new", {"title": "Gone for good"})[1].split("/")[-1]
    post(f"/delete/{mid}", {}); post("/trash/empty", {})
    assert "Trash is empty" in get("/trash")

def test_duplicate_over_http_and_edited_label():
    mid = post("/new", {"title": "Dup src"})[1].split("/")[-1]
    post(f"/notes/{mid}", {"text": "one two three"})
    st, loc = post(f"/duplicate/{mid}", {})
    assert st == 303 and loc.startswith("/meeting/") and loc.split("/")[-1] != mid
    html = get(loc)
    assert 'value="Copy of Dup src"' in html and "one two three" in html
    assert "3 words" in get(f"/meeting/{mid}") and "edited today" in get(f"/meeting/{mid}")
