import json, os, stat, subprocess, sys, tempfile, time
import pytest
from iris import cloud as CL, store as S

PORT = 18492


@pytest.fixture(scope="module")
def relay():
    d = tempfile.mkdtemp()
    p = subprocess.Popen([sys.executable, "iris/sync_server.py", "--dir", d, "--token", "tok", "--port", str(PORT)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    yield d
    p.kill()


def _store():
    d = tempfile.mkdtemp()
    mid = S.new_meeting(d, "Cloud test")
    S.write_text(d, mid, "notes.md", "# Cloud test\n- decided")
    S.write_text(d, mid, "transcript.md", "[00:00] secret words")
    return d, mid


def test_save_is_owner_only_and_rejects_plain_http():
    d, _ = _store()
    CL.save(d, "https://x.test/sync", "tok")
    assert stat.S_IMODE(os.stat(os.path.join(d, ".cloud.json")).st_mode) == 0o600
    assert CL.status(d)["linked"] and not CL.status(d)["transcripts"]
    with pytest.raises(ValueError):
        CL.save(d, "http://evil.example/sync", "tok")
    CL.forget(d)
    assert not CL.status(d)["linked"]


def test_token_is_kept_when_settings_saved_without_one():
    d, _ = _store()
    CL.save(d, "https://x.test/sync", "keepme")
    CL.save(d, "https://x.test/sync", "", transcripts=True)
    assert CL.load(d)["token"] == "keepme" and CL.status(d)["transcripts"]


def test_sync_now_sends_notes_not_transcript(relay):
    d, mid = _store()
    CL.save(d, f"http://127.0.0.1:{PORT}", "tok")
    r = CL.sync_now(d)
    assert r["pushed"] == 1
    b = json.load(open(os.path.join(relay, mid, "bundle.json")))
    assert "notes" in b and "transcript" not in b
    assert CL.sync_now(d)["pushed"] == 0 and CL.status(d)["last"]


def test_sync_now_requires_link():
    d, _ = _store()
    with pytest.raises(RuntimeError):
        CL.sync_now(d)


def test_auto_sync_is_silent_when_unlinked_or_off_and_never_raises():
    d, _ = _store()
    assert CL.auto_sync(d) is None                       # not linked
    CL.save(d, "https://127.0.0.1:1/sync", "tok")        # linked but unreachable
    assert CL.auto_sync(d) is None                       # swallowed, no exception
    CL.set_auto(d, False)
    assert CL.auto_sync(d) is None and CL.load(d)["auto"] is False
    with pytest.raises(RuntimeError):
        CL.set_auto(tempfile.mkdtemp(), True)
