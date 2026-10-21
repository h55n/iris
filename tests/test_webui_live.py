"""Live web UI: real HTTP server, rename and delete flows over POST."""
import json, os, subprocess, time, urllib.request, urllib.parse
import pytest

STORE = "/tmp/iris-webui-store"
PORT = 18473

@pytest.fixture(scope="module", autouse=True)
def server():
    os.system(f"rm -rf {STORE}")
    os.makedirs(STORE)
    mid = "20261021-0000-abc123"
    d = os.path.join(STORE, mid)
    os.makedirs(d)
    json.dump({"id": mid, "title": mid, "created": time.time()}, open(os.path.join(d, "meta.json"), "w"))
    open(os.path.join(d, "notes.md"), "w").write("## Decisions\n- keep it local")
    env = dict(os.environ, IRIS_STORE=STORE)
    srv = subprocess.Popen(["python3", "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    yield mid
    srv.kill()

def _post(path, data):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
        data=urllib.parse.urlencode(data).encode(), method="POST")
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    return opener.open(req)

def test_index_lists_meeting(server):
    html = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/").read().decode()
    assert server in html

def test_rename_updates_title(server):
    _post(f"/rename/{server}", {"title": "weekly sync"})
    meta = json.load(open(os.path.join(STORE, server, "meta.json")))
    assert meta["title"] == "weekly sync"

def test_meeting_page_shows_new_title(server):
    html = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/meeting/{server}").read().decode()
    assert "weekly sync" in html and "keep it local" in html

def test_path_traversal_rejected(server):
    try:
        _post("/rename/..%2F..%2Ftmp", {"title": "x"})
    except Exception:
        pass
    assert os.path.isdir(os.path.join(STORE, server))

def test_delete_removes_meeting(server):
    _post(f"/delete/{server}", {})
    assert not os.path.isdir(os.path.join(STORE, server))
