"""Live ingest-server guard rails: auth, path, size checks (no whisper needed)."""
import os, subprocess, time, urllib.request, urllib.error
import pytest

STORE = "/tmp/iris-ingest-store"
PORT = 18472

@pytest.fixture(scope="module", autouse=True)
def server():
    os.system(f"rm -rf {STORE}")
    os.makedirs(STORE)
    srv = subprocess.Popen(["python3", "iris/ingest_server.py", "--store", STORE,
                            "--token", "t0ken", "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    yield
    srv.kill()

def _post(path, body=b"x" * 2000, token=None, title=None):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=body, method="POST")
    if token: req.add_header("X-Convo-Token", token)
    if title: req.add_header("X-Iris-Title", title)
    try:
        return urllib.request.urlopen(req).getcode()
    except urllib.error.HTTPError as e:
        return e.code

def test_no_token_rejected(server):
    assert _post("/ingest") == 403

def test_wrong_token_rejected(server):
    assert _post("/ingest", token="nope") == 403

def test_wrong_path_404(server):
    assert _post("/nope", token="t0ken") == 404

def test_tiny_audio_rejected(server):
    assert _post("/ingest", body=b"ab", token="t0ken") == 400
