"""Zero-claims 'verified' wording and sync-aware privacy copy (Nov 4:
main review found the UI said 'verified' when 0/0 claims were checked,
and 'Audio never leaves it' without naming what syncs once linked)."""
import json, os, tempfile
from iris import store as S
from iris import webui

def _meta(integrity=None, encrypted=False):
    m = {"created": 1700000000, "title": "t"}
    if integrity is not None: m["integrity"] = integrity
    if encrypted: m["encrypted"] = True
    return m

def test_nav_item_hides_pill_when_zero_checked():
    html = webui._nav_item("m1", _meta({"checked": 0, "passed": 0}), "")
    assert "verified" not in html

def test_nav_item_shows_pill_when_checked():
    html = webui._nav_item("m1", _meta({"checked": 5, "passed": 5}), "")
    assert "5/5 verified" in html

def test_saved_subline_unlinked_no_integrity():
    d = tempfile.mkdtemp()
    line = webui._saved_subline(_meta(), d)
    assert line == "saved on this device. Audio never leaves it."

def test_saved_subline_verified_only_when_checked():
    d = tempfile.mkdtemp()
    assert webui._saved_subline(_meta({"checked": 3, "passed": 3}), d).startswith("verified, saved")
    assert "verified" not in webui._saved_subline(_meta({"checked": 0, "passed": 0}), d)

def test_saved_subline_encrypted_leads():
    d = tempfile.mkdtemp()
    assert webui._saved_subline(_meta(encrypted=True), d).startswith("encrypted, saved")

def test_saved_subline_linked_names_what_syncs():
    d = tempfile.mkdtemp()
    json.dump({"token": "t", "server": "https://x.test/sync"}, open(os.path.join(d, ".cloud.json"), "w"))
    line = webui._saved_subline(_meta(), d)
    assert "notes sync to your linked cloud" in line and "Audio never leaves it." in line

def test_saved_subline_linked_with_transcripts():
    d = tempfile.mkdtemp()
    json.dump({"token": "t", "server": "https://x.test/sync", "transcripts": True}, open(os.path.join(d, ".cloud.json"), "w"))
    assert "notes and transcripts sync" in webui._saved_subline(_meta(), d)
