from iris import store as s

def test_list_meetings_skips_non_meetings(tmp_path):
    s.new_meeting(str(tmp_path), "a")
    (tmp_path / "random-file.txt").write_text("junk")
    (tmp_path / "emptydir").mkdir()
    assert len(s.list_meetings(str(tmp_path))) == 1

def test_list_meetings_order(tmp_path):
    import time
    a = s.new_meeting(str(tmp_path), "first")
    time.sleep(0.02)
    b = s.new_meeting(str(tmp_path), "second")
    assert s.list_meetings(str(tmp_path), reverse=True)[0] == max(a, b)

def test_sweep_dry_run_deletes_nothing(tmp_path):
    import time, json, os
    mid = s.new_meeting(str(tmp_path), "old")
    s.attach_audio(str(tmp_path), mid, __file__)  # any file stands in for audio
    meta = json.load(open(tmp_path / mid / "meta.json"))
    meta["created"] = time.time() - 9 * 86400  # 9 days old
    json.dump(meta, open(tmp_path / mid / "meta.json", "w"))
    would = s.sweep(str(tmp_path), dry_run=True)
    assert would and all(os.path.exists(p) for p in would)
    gone = s.sweep(str(tmp_path))
    assert gone and all(not os.path.exists(p) for p in gone)

def test_attach_audio_twice_keeps_both(tmp_path):
    from iris import store
    d = str(tmp_path / "store")
    mid = store.new_meeting(d, "two parts")
    a = tmp_path / "part1.wav"; a.write_bytes(b"first")
    b = tmp_path / "part2.WAV"; b.write_bytes(b"second-larger")
    p1 = store.attach_audio(d, mid, str(a))
    p2 = store.attach_audio(d, mid, str(b))
    assert p1 != p2
    assert open(p1, "rb").read() == b"first"
    assert open(p2, "rb").read() == b"second-larger"
    import json, os
    meta = json.load(open(os.path.join(d, mid, "meta.json")))
    assert len(meta["audio_files"]) == 2

def test_sweep_deletes_all_parts_of_old_recording(tmp_path):
    from iris import store
    import json, os, time
    d = str(tmp_path / "store")
    mid = store.new_meeting(d, "old two-parter")
    a = tmp_path / "p1.wav"; a.write_bytes(b"one")
    b = tmp_path / "p2.wav"; b.write_bytes(b"two")
    store.attach_audio(d, mid, str(a)); store.attach_audio(d, mid, str(b))
    mp = os.path.join(d, mid, "meta.json")
    meta = json.load(open(mp)); meta["created"] = time.time() - 9 * 86400
    json.dump(meta, open(mp, "w"))
    deleted = store.sweep(d)
    assert len(deleted) == 2
    assert not [f for f in os.listdir(os.path.join(d, mid)) if f.endswith(".wav")]
    assert os.path.exists(mp)  # meta stays
