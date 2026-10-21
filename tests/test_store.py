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
