import json, os, pytest
from iris import cli, store as S, library as L

def run(monkeypatch, store, *args):
    monkeypatch.setattr(cli, "STORE", str(store)); monkeypatch.setattr("sys.argv", ["iris", *args]); cli.main([])

def test_folder_note_pin_move_roundtrip(tmp_path, monkeypatch, capsys):
    run(monkeypatch, tmp_path, "folder", "new", "Project Alpha")
    fid = capsys.readouterr().out.strip()
    run(monkeypatch, tmp_path, "note", "Kickoff", "--in", "project alpha")
    mid = capsys.readouterr().out.strip()
    meta = S._load_meta(str(tmp_path), mid)
    assert meta["title"] == "Kickoff" and meta["folder"] == fid
    run(monkeypatch, tmp_path, "pin", mid); assert S._load_meta(str(tmp_path), mid)["pinned"] is True
    run(monkeypatch, tmp_path, "unpin", mid); assert "pinned" not in S._load_meta(str(tmp_path), mid)
    run(monkeypatch, tmp_path, "move", mid, "none"); assert "folder" not in S._load_meta(str(tmp_path), mid)
    run(monkeypatch, tmp_path, "move", mid, "Project Alpha"); assert S._load_meta(str(tmp_path), mid)["folder"] == fid
    run(monkeypatch, tmp_path, "folders")
    assert f"{fid}  Project Alpha  (1)" in capsys.readouterr().out

def test_unknown_folder_and_empty_name_are_errors(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit): run(monkeypatch, tmp_path, "note", "x", "--in", "ghost")
    assert "no such folder: ghost" in capsys.readouterr().err
    with pytest.raises(SystemExit): run(monkeypatch, tmp_path, "folder", "new", "  ")
    assert "folder needs a name" in capsys.readouterr().err
    with pytest.raises(SystemExit): run(monkeypatch, tmp_path, "move")
