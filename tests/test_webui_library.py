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
