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
