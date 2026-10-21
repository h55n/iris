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
    open(os.path.join(d, "transcript.md"), "w").write("[00:05] Speaker 1: retention stays seven days")
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


def _get(path):
    return urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}").read().decode()

def _mk_search_meeting():
    # the shared fixture meeting may already be deleted by test_delete_*;
    # search tests create their own so they are order-independent
    mid = "20261021-0001-sea777"
    d = os.path.join(STORE, mid)
    os.makedirs(d, exist_ok=True)
    json.dump({"id": mid, "title": mid, "created": time.time()}, open(os.path.join(d, "meta.json"), "w"))
    open(os.path.join(d, "notes.md"), "w").write("## Decisions\n- keep it local")
    open(os.path.join(d, "transcript.md"), "w").write("[00:05] Speaker 1: retention stays seven days")
    return mid

def test_search_finds_note_text(server):
    mid = _mk_search_meeting()
    html = _get("/search?q=" + urllib.parse.quote("keep it local"))
    assert "keep it local" in html and mid in html

def test_search_finds_transcript_text(server):
    _mk_search_meeting()
    html = _get("/search?q=retention")
    assert "seven days" in html

def test_search_no_match(server):
    _mk_search_meeting()
    html = _get("/search?q=zzzznope")
    assert "keep it local" not in html

def test_search_empty_query(server):
    html = _get("/search?q=")
    assert "Search" in html

def test_raw_download(server):
    mid = _mk_search_meeting()
    body = _get(f"/raw/{mid}/transcript.md")
    assert "retention stays seven days" in body

def test_raw_rejects_traversal(server):
    # the handler renders its "not found" page and never touches the filesystem
    body = ""
    try:
        body = _get("/raw/..%2f..%2fetc/transcript.md")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    assert "root:" not in body and "[00:05]" not in body

def test_raw_rejects_unknown_file(server):
    mid = _mk_search_meeting()
    try:
        _get(f"/raw/{mid}/secret.txt")
        assert False, "unknown file should 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404

def test_rename_caps_long_title(server):
    mid = _mk_search_meeting()
    _post(f"/rename/{mid}", {"title": "x" * 500})
    meta = json.load(open(os.path.join(STORE, mid, "meta.json")))
    assert len(meta["title"]) == 120

def test_title_html_escaped_in_page(server):
    import html as H
    mid = _mk_search_meeting()
    payload = '<script>alert(1)</script>'
    _post(f"/rename/{mid}", {"title": payload})
    body = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/meeting/{mid}").read().decode()
    assert payload not in body and H.escape(payload) in body

def test_missing_meeting_is_a_real_404(server):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/meeting/20990101-0000-ffffff")
        assert False, "should 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404

def test_raw_download_missing_file_404s(server):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/raw/20990101-0000-ffffff/notes.md")
        assert False, "unknown meeting should 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404

def test_locked_meeting_shows_friendly_page_not_500(server):
    from iris import store as S, crypto as C
    key = "/tmp/iris-webui-lock-test.txt"
    if os.path.exists(key): os.remove(key)
    C.generate_key(key)
    mid = _mk_search_meeting()
    S.encrypt_meeting(STORE, mid, key)
    html = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/meeting/{mid}").read().decode()
    assert "locked" in html.lower() and "Traceback" not in html
    # restore plaintext so later tests see the meeting again
    texts = S.decrypt_meeting(STORE, mid, key)
    for n, t in texts.items():
        open(os.path.join(STORE, mid, n), "w").write(t)
        p = os.path.join(STORE, mid, n + ".age")
        if os.path.exists(p): os.remove(p)
    mp = os.path.join(STORE, mid, "meta.json")
    m = json.load(open(mp)); m["encrypted"] = False
    json.dump(m, open(mp, "w"))

