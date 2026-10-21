"""Folders sync between devices, and a newer local edit is never overwritten."""
import json, os, subprocess, time
import pytest
from iris import library as L, store as S, sync as Y

A, B, RELAY = "/tmp/iris-lib-A", "/tmp/iris-lib-B", "/tmp/iris-lib-relay"
PORT = 18481
URL = f"http://127.0.0.1:{PORT}"

@pytest.fixture(scope="module", autouse=True)
def server():
    os.system(f"rm -rf {A} {B} {RELAY}")
    for d in (A, B, RELAY): os.makedirs(d)
    srv = subprocess.Popen(["python3", "iris/sync_server.py", "--dir", RELAY, "--token", "t", "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8); yield; srv.kill()

def test_folders_and_pins_reach_other_device():
    f = L.create_folder(A, "Project Alpha")
    mid = L.new_note(A, "Spec", folder=f["id"]); L.set_pinned(A, mid, True)
    assert Y.push_folders(A, URL, "t") is True
    Y.push_changed(A, URL, "t")
    assert Y.push_folders(A, URL, "t") is False       # unchanged: nothing resent
    Y.pull_all(B, URL, "t")
    assert [x["name"] for x in L.list_folders(B)] == ["Project Alpha"]
    meta = S._load_meta(B, mid)
    assert meta["folder"] == f["id"] and meta["pinned"] is True
    assert "_folders" not in os.listdir(B)             # not mistaken for a meeting

def test_newer_local_edit_survives_pull():
    mid = [m for m in S.list_meetings(B)][0]
    L.save_notes(B, mid, "edited on B after sync")
    Y.pull_all(B, URL, "t", since=0.0)
    assert open(os.path.join(B, mid, "notes.md")).read() == "edited on B after sync"

def test_merge_folders_never_deletes_or_renames_local():
    L.create_folder(B, "B only")
    remote = [{"id": L.list_folders(B)[0]["id"], "name": "renamed remotely"}, {"id": "f-new", "name": "New"}]
    assert Y.merge_folders(B, remote) == 1
    names = {f["name"] for f in L.list_folders(B)}
    assert "renamed remotely" not in names and "New" in names and "B only" in names

def test_trash_and_stray_dirs_never_sync():
    mid = L.new_note(A, "will be trashed"); L.trash_note(A, mid)
    os.makedirs(os.path.join(A, "stray-dir"), exist_ok=True)
    pushed, _ = Y.push_changed(A, URL, "t")
    assert ".trash" not in pushed and "stray-dir" not in pushed and mid not in pushed
