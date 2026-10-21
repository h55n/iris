import os, json
from iris import store as S, crypto as C

KEY = "/tmp/iris-store-test-key.txt"
STORE = "/tmp/iris-store-test"

def setup_module(m):
    os.system(f"rm -rf {STORE} {KEY}")
    os.makedirs(STORE)
    C.generate_key(KEY)

def test_encrypt_meeting_removes_plaintext_keeps_age():
    mid = S.new_meeting(STORE)
    S.write_text(STORE, mid, "transcript.md", "[00:01] hello Priya")
    S.write_text(STORE, mid, "notes.md", "decision: ship Friday")
    done = S.encrypt_meeting(STORE, mid, KEY)
    d = os.path.join(STORE, mid)
    assert set(done) == {"transcript.md.age", "notes.md.age"}
    assert not os.path.exists(os.path.join(d, "transcript.md"))
    assert "Priya" not in open(os.path.join(d, "transcript.md.age")).read()
    assert S.is_encrypted(STORE, mid)

def test_decrypt_meeting_roundtrip():
    mid = sorted(os.listdir(STORE))[0]
    out = S.decrypt_meeting(STORE, mid, KEY)
    assert out["transcript.md"] == "[00:01] hello Priya"
    assert "ship Friday" in out["notes.md"]

def test_search_skips_locked_meeting_without_key():
    mid = sorted(os.listdir(STORE))[0]  # encrypted by the first test
    hits = S.search(STORE, "Priya", key_path="/tmp/definitely-not-a-key.txt")
    assert hits == []
    hits2 = S.search(STORE, "Priya", key_path=KEY)
    assert hits2 and hits2[0]["meeting"] == mid
