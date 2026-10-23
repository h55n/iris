"""Incremental push: unchanged meetings are not re-sent."""
import os, subprocess, time
import pytest
from iris import store as S, sync as Y

A = "/tmp/iris-inc-A"; RELAY = "/tmp/iris-inc-relay"
PORT = 18479

@pytest.fixture(scope="module", autouse=True)
def server():
    os.system(f"rm -rf {A} {RELAY}")
    for d in (A, RELAY): os.makedirs(d)
    srv = subprocess.Popen(["python3", "iris/sync_server.py", "--dir", RELAY,
                            "--token", "t", "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    yield
    srv.kill()

def _mk(store_dir, title):
    mid = S.new_meeting(store_dir, title)
    S.write_text(store_dir, mid, "notes.md", f"# {title}")
    return mid

def test_second_push_sends_nothing():
    server = f"http://127.0.0.1:{PORT}"
    _mk(A, "one"); _mk(A, "two")
    pushed, skipped = Y.push_changed(A, server, "t")
    assert len(pushed) == 2 and not skipped
    pushed2, skipped2 = Y.push_changed(A, server, "t")
    assert pushed2 == [] and len(skipped2) == 2

def test_edit_triggers_repush():
    server = f"http://127.0.0.1:{PORT}"
    mid = sorted(d for d in os.listdir(A) if os.path.isdir(os.path.join(A, d)))[0]
    S.write_text(A, mid, "notes.md", "# changed")
    pushed, skipped = Y.push_changed(A, server, "t")
    assert pushed == [mid]

def test_bundle_hash_stable(tmp_path):
    from iris import sync as Y
    mid = S.new_meeting(str(tmp_path), "hash me")
    S.write_text(str(tmp_path), mid, "transcript.md", "[00:01] same bytes")
    assert Y.bundle_hash(str(tmp_path), mid) == Y.bundle_hash(str(tmp_path), mid)

def test_bundle_hash_changes_with_content(tmp_path):
    from iris import sync as Y
    mid = S.new_meeting(str(tmp_path), "hash me")
    S.write_text(str(tmp_path), mid, "transcript.md", "[00:01] v1")
    h1 = Y.bundle_hash(str(tmp_path), mid)
    S.write_text(str(tmp_path), mid, "transcript.md", "[00:01] v2")
    assert Y.bundle_hash(str(tmp_path), mid) != h1

def test_push_changed_skips_corrupt_meeting(tmp_path, monkeypatch):
    from iris import sync as Y
    import os, json
    d = str(tmp_path / "store")
    _mk(d, "good-one")
    # make a corrupt meeting alongside
    bad = os.path.join(d, "20261010-0000-corrupt")
    os.makedirs(bad, exist_ok=True)
    open(os.path.join(bad, "meta.json"), "w").write("{broken")
    pushed_to = []
    monkeypatch.setattr(Y, "push", lambda sd, mid, srv, tok: pushed_to.append(mid))
    pushed, skipped = Y.push_changed(d, "http://x", "t")
    assert "20261010-0000-corrupt" in skipped and "20261010-0000-corrupt" not in pushed_to
    assert pushed_to  # the good meeting still pushed


def test_pull_skips_browser_encrypted_bundles(monkeypatch, tmp_path):
    from iris import sync as SY, store as S
    mid = S.new_meeting(str(tmp_path), "Local copy")
    S.write_text(str(tmp_path), mid, "notes.md", "# Local copy\n- keep me")
    bundles = {mid: {"meta": {"title": "Encrypted note", "browser_encrypted": True},
                     "notes_ct": {"v": 1, "ct": "..."}}}
    monkeypatch.setattr(SY, "_req", lambda url, token, data=None:
                        {"meetings": [{"id": mid, "ts": 1}]} if "/list" in url else bundles[mid])
    got = SY.pull_all(str(tmp_path), "https://x.test/sync", "tok")
    assert got == [mid]  # seen, so it is not re-pulled forever
    assert "keep me" in open(os.path.join(str(tmp_path), mid, "notes.md")).read()
    assert "Encrypted note" not in open(os.path.join(str(tmp_path), mid, "meta.json")).read()
