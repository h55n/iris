"""Live sync roundtrip: real sync_server process, two device stores, encrypted
meeting travels as ciphertext, relay disk holds NO plaintext."""
import os, subprocess, time, json
import pytest
from iris import store as S, crypto as C, sync as Y

KEY = "/tmp/convo-synctest-key.txt"
A = "/tmp/convo-synctest-A"; B = "/tmp/convo-synctest-B"; RELAY = "/tmp/convo-synctest-relay"
PORT = 18471

@pytest.fixture(scope="module", autouse=True)
def setup():
    os.system(f"rm -rf {KEY} {A} {B} {RELAY}")
    for d in (A, B, RELAY): os.makedirs(d)
    if not os.path.exists(KEY): C.generate_key(KEY)
    srv = subprocess.Popen(["python3", "iris/sync_server.py", "--dir", RELAY,
                            "--token", "t0ken", "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    yield
    srv.kill()

def _mk_meeting(store_dir):
    mid = S.new_meeting(store_dir, "sync test")
    S.write_text(store_dir, mid, "transcript.md", "[00:01] retention stays seven days")
    S.write_text(store_dir, mid, "notes.md", "## Decisions\n- retention 7 days")
    S.encrypt_meeting(store_dir, mid, KEY)
    return mid

def test_push_ciphertext_pull_on_other_device():
    server = f"http://127.0.0.1:{PORT}"
    mid = _mk_meeting(A)
    Y.push(A, mid, server, "t0ken")
    # relay holds only ciphertext
    bundle = json.load(open(os.path.join(RELAY, mid, "bundle.json")))
    assert "transcript_age" in bundle and "transcript" not in bundle
    assert "seven days" not in json.dumps(bundle)
    # device B pulls and decrypts with the same key
    got = Y.pull_all(B, server, "t0ken", 0.0)
    assert got == [mid]
    texts = S.decrypt_meeting(B, mid, KEY)
    assert "seven days" in texts["transcript.md"]
    assert "retention 7 days" in texts["notes.md"]

def test_wrong_token_rejected():
    mid = os.listdir(A)[0]
    try:
        Y.push(A, mid, f"http://127.0.0.1:{PORT}", "WRONG")
        assert False, "should 403"
    except Exception as e:
        assert "403" in str(e)
