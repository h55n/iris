import json, os, pytest
from iris import library as L, store as S

def test_folder_create_rename_delete_keeps_notes(tmp_path):
    d = str(tmp_path)
    f = L.create_folder(d, "  Project   Alpha ")
    assert f["name"] == "Project Alpha"
    mid = L.new_note(d, "Spec", folder=f["id"])
    assert S._load_meta(d, mid)["folder"] == f["id"]
    assert L.rename_folder(d, f["id"], "Alpha v2") and L.list_folders(d)[0]["name"] == "Alpha v2"
    assert L.delete_folder(d, f["id"]) and L.list_folders(d) == []
    assert "folder" not in S._load_meta(d, mid) and os.path.isdir(tmp_path / mid)

def test_empty_folder_name_rejected(tmp_path):
    with pytest.raises(ValueError):
        L.create_folder(str(tmp_path), "   ")

def test_move_to_missing_folder_fails_and_none_clears(tmp_path):
    d = str(tmp_path); mid = L.new_note(d, "x")
    with pytest.raises(ValueError):
        L.move(d, mid, "f-nope")
    f = L.create_folder(d, "A"); L.move(d, mid, f["id"]); L.move(d, mid, None)
    assert "folder" not in S._load_meta(d, mid)

def test_pin_unpin(tmp_path):
    d = str(tmp_path); mid = L.new_note(d, "x")
    L.set_pinned(d, mid, True); assert S._load_meta(d, mid)["pinned"] is True
    L.set_pinned(d, mid, False); assert "pinned" not in S._load_meta(d, mid)

def test_save_notes_plain(tmp_path):
    d = str(tmp_path); mid = L.new_note(d, "x")
    L.save_notes(d, mid, "# Hi\r\n- a")
    assert open(tmp_path / mid / "notes.md").read() == "# Hi\n- a"
    assert "edited" in S._load_meta(d, mid)

def test_corrupt_folders_file_is_empty_list(tmp_path):
    (tmp_path / "_folders.json").write_text("{nope")
    assert L.list_folders(str(tmp_path)) == []

def test_save_notes_keeps_encrypted_meeting_encrypted(tmp_path):
    from iris import crypto as C
    key = str(tmp_path / "k.txt"); C.generate_key(key)
    d = str(tmp_path / "store"); os.makedirs(d)
    mid = L.new_note(d, "secret")
    S.encrypt_meeting(d, mid, key)
    L.save_notes(d, mid, "launch code is plants", key_path=key)
    assert not os.path.exists(os.path.join(d, mid, "notes.md"))
    assert S.decrypt_meeting(d, mid, key)["notes.md"] == "launch code is plants"
    assert b"plants" not in open(os.path.join(d, mid, "notes.md.age"), "rb").read()

def _tm(tmp_path, tr, notes="x"):
    d = str(tmp_path); mid = L.new_note(d, "m")
    S.write_text(d, mid, "transcript.md", tr); S.write_text(d, mid, "notes.md", notes)
    return d, mid

def test_rename_speaker_only_touches_labels(tmp_path):
    d, mid = _tm(tmp_path, "[00:01] Speaker 2: I told Speaker 2: hi\n[00:05] Speaker 1: ok\n[00:09] Speaker 22: no",
                 "## Summary\nSpeaker 2 owns the plan. Speaker 22 stays.")
    assert L.rename_speaker(d, mid, "Speaker 2", "Priya") == 1
    tr = open(os.path.join(d, mid, "transcript.md")).read()
    assert tr.splitlines()[0] == "[00:01] Priya: I told Speaker 2: hi"
    assert "[00:09] Speaker 22: no" in tr and "[00:05] Speaker 1: ok" in tr
    notes = open(os.path.join(d, mid, "notes.md")).read()
    assert "Priya owns the plan" in notes and "Speaker 22 stays" in notes

def test_rename_speaker_rejects_bad_names(tmp_path):
    d, mid = _tm(tmp_path, "[00:01] Speaker 2: hi")
    for bad in ("", "a<script>", "x" * 40, "-lead"):
        with pytest.raises(ValueError):
            L.rename_speaker(d, mid, "Speaker 2", bad)

def test_rename_speaker_supports_devanagari_and_encrypted(tmp_path):
    from iris import crypto as C
    key = str(tmp_path / "k.txt"); C.generate_key(key)
    d, mid = _tm(tmp_path, "[00:01] Speaker 1: namaste")
    S.encrypt_meeting(d, mid, key)
    assert L.rename_speaker(d, mid, "Speaker 1", "प्रिया", key_path=key) == 1
    assert not os.path.exists(os.path.join(d, mid, "transcript.md"))
    assert S.decrypt_meeting(d, mid, key)["transcript.md"].startswith("[00:01] प्रिया: ")

def test_rename_speaker_unknown_label_changes_nothing(tmp_path):
    d, mid = _tm(tmp_path, "[00:01] Speaker 1: hi")
    assert L.rename_speaker(d, mid, "Speaker 9", "Ravi") == 0

def test_reorder_folders(tmp_path):
    d = str(tmp_path)
    a, b, c = (L.create_folder(d, n)["id"] for n in "ABC")
    assert L.reorder_folders(d, [c, a]) is True
    assert [f["id"] for f in L.list_folders(d)] == [c, a, b]
    assert L.reorder_folders(d, [c, a]) is False
    assert L.reorder_folders(d, ["f-ghost", c]) is False

def test_reorder_notes_sets_order_and_ignores_unknown(tmp_path):
    d = str(tmp_path)
    x, y = L.new_note(d, "x"), L.new_note(d, "y")
    assert L.reorder_notes(d, [y, "nope", x, y]) == 2
    assert S._load_meta(d, y)["order"] == 0 and S._load_meta(d, x)["order"] == 1
    assert L.reorder_notes(d, [y, x]) == 0

def test_order_key_puts_manual_first():
    ms = [{"created": 5}, {"order": 1, "created": 1}, {"order": 0, "created": 2}, {"created": 9}]
    assert [m["created"] for m in sorted(ms, key=L.order_key)] == [2, 1, 9, 5]
