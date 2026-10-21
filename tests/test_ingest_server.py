"""Live ingest-server guard rails: auth, path, size checks (no whisper needed)."""
import json, os, subprocess, time, urllib.request, urllib.error
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
    if token: req.add_header("X-Iris-Token", token)
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

def test_huge_audio_rejected(server):
    assert _post("/ingest", body=b"", token="t0ken") in (400,)  # empty
    # claim a huge Content-Length without sending it: server must refuse on the header alone
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", PORT)
    conn.request("POST", "/ingest", body=b"x" * 2000,
                 headers={"X-Iris-Token": "t0ken",
                          "Content-Length": str(600 * 1024 * 1024)})
    # server reads the header first; it should 413 without needing the body
    try:
        code = conn.getresponse().status
    except Exception:
        code = None  # connection reset is also an acceptable refusal
    conn.close()
    assert code in (413, None)


def test_legacy_convo_token_header_still_accepted(server):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/nope", data=b"x" * 2000, method="POST")
    req.add_header("X-Convo-Token", "t0ken")  # old APK header -> must still auth (404 not 403)
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        assert e.code == 404

def test_legacy_convo_title_header_preference():
    from iris.ingest_server import _meeting_title
    assert _meeting_title({"X-Iris-Title": "standup", "X-Convo-Title": "old"}) == "standup"
    assert _meeting_title({"X-Convo-Title": "old-apk title"}) == "old-apk title"
    assert _meeting_title({}) == ""

def test_bad_content_length_400_not_crash(server):
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", PORT)
    conn.putrequest("POST", "/ingest")
    conn.putheader("X-Iris-Token", "t0ken")
    conn.putheader("Content-Length", "not-a-number")
    conn.endheaders(b"x" * 2000)
    try:
        code = conn.getresponse().status
    except Exception:
        code = None
    conn.close()
    assert code == 400
    assert _post("/nope", token="t0ken") == 404  # server still alive

def test_pipeline_failure_returns_500_keeps_audio(server):
    # 2KB of garbage is a valid-size upload but not transcribable audio
    code = _post("/ingest", body=b"garbage" * 400, token="t0ken", title="broken")
    assert code == 500
    import glob
    meetings = [d for d in glob.glob(os.path.join(STORE, "*")) if os.path.isdir(d)]
    broken = [d for d in meetings
              if json.load(open(os.path.join(d, "meta.json"))).get("title") == "broken"]
    assert broken and os.path.exists(os.path.join(broken[0], "audio.wav"))  # audio kept
