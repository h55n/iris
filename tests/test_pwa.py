"""Installable web app: manifest, service worker, icons, token gate, upload API."""
import json, os, subprocess, sys, time, urllib.request, urllib.error
import pytest

STORE, PORT = "/tmp/iris-pwa-store", 18495
BASE = f"http://127.0.0.1:{PORT}"

@pytest.fixture(scope="module")
def server():
    os.system(f"rm -rf {STORE}"); os.makedirs(STORE)
    srv = subprocess.Popen([sys.executable, "iris/webui.py", "--store", STORE, "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0); yield; srv.kill()

def get(path, **kw):
    return urllib.request.urlopen(urllib.request.Request(BASE + path, **kw))

def test_manifest_is_installable(server):
    m = json.load(get("/manifest.webmanifest"))
    assert m["display"] == "standalone" and m["start_url"] == "/"
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes
    for i in m["icons"]:
        r = get(i["src"]); assert r.headers["Content-Type"] == "image/png" and r.read(4) == b"\x89PNG"

def test_service_worker_and_head_tags(server):
    sw = get("/sw.js"); assert sw.headers["Content-Type"].startswith("text/javascript")
    assert b"fetch" in sw.read()
    html = get("/").read().decode()
    assert 'rel=manifest' in html and "serviceWorker" in html and "theme-color" in html

def test_record_page_and_sidebar_link(server):
    assert "MediaRecorder" in get("/record").read().decode()
    assert 'href="/record"' in get("/").read().decode()

def test_upload_api_rejects_tiny_audio(server):
    req = urllib.request.Request(BASE + "/api/record", data=b"x" * 10, method="POST", headers={"Content-Type": "audio/webm"})
    with pytest.raises(urllib.error.HTTPError) as e: urllib.request.urlopen(req)
    assert e.value.code == 400

def test_upload_keeps_audio_when_transcription_fails(server):
    junk = b"not really audio " * 200
    req = urllib.request.Request(BASE + "/api/record", data=junk, method="POST",
                                 headers={"Content-Type": "audio/webm", "X-Iris-Title": "Standup%20test"})
    try:
        out = json.load(urllib.request.urlopen(req)); mid = out["meeting"]
    except urllib.error.HTTPError as e:
        assert e.code == 500; mid = json.load(e)["meeting"]
    assert os.path.exists(os.path.join(STORE, mid, "audio.webm"))

def test_token_gate(tmp_path):
    port = 18496; d = str(tmp_path)
    srv = subprocess.Popen([sys.executable, "iris/webui.py", "--store", d, "--port", str(port), "--token", "sekrit"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with pytest.raises(urllib.error.HTTPError) as e: urllib.request.urlopen(f"http://127.0.0.1:{port}/")
        assert e.value.code == 401
        class NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.build_opener(NoRedir).open(f"http://127.0.0.1:{port}/?t=sekrit")
        assert e.value.code == 303 and "iris_t=sekrit" in e.value.headers["Set-Cookie"]
        r = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/", headers={"Cookie": "iris_t=sekrit"}))
        assert r.status == 200
        assert urllib.request.urlopen(f"http://127.0.0.1:{port}/manifest.webmanifest").status == 200
    finally:
        srv.kill()

def test_refuses_network_bind_without_token():
    r = subprocess.run([sys.executable, "iris/webui.py", "--host", "0.0.0.0", "--port", "18497"], capture_output=True, text=True)
    assert r.returncode != 0 and "--token" in (r.stderr + r.stdout)
