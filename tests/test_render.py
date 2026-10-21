from iris.render import render_notes

NOTES = {
    "summary": "quick sync",
    "decisions": [{"text": "ship Friday", "evidence": "we ship Friday", "at": "00:14"}],
    "action_items": [{"text": "own sync", "owner": "Priya", "evidence": "Priya owns sync", "at": "00:23"}],
    "unverified_action_items": [{"text": "buy servers", "unverified_reason": "owner not mentioned"}],
    "integrity": {"checked": 3, "passed": 2},
}

def test_sections_present():
    md = render_notes("m1", NOTES, [])
    for h in ("## Summary", "## Decisions", "## Action items"):
        assert h in md

def test_receipts_render_with_timestamps():
    md = render_notes("m1", NOTES, [])
    assert '"we ship Friday" [00:14]' in md

def test_unverified_section_labeled():
    md = render_notes("m1", NOTES, [])
    assert "Unverified" in md and "owner not mentioned" in md

def test_integrity_line_counts():
    md = render_notes("m1", NOTES, [])
    assert "2/3 claims verified" in md

def test_missing_owner_renders_cleanly():
    n = dict(NOTES); n["action_items"] = [{"text": "t", "evidence": "e", "at": "00:01"}]
    assert "- [ ] t  " in render_notes("m1", n, [])

def test_render_notes_tolerates_partial_items():
    from iris import render
    md = render.render_notes("m1", {"summary": "s",
        "decisions": [{"text": "keep it local"}],          # no evidence/at
        "action_items": [{"evidence": "q", "at": "00:01"}]}, [])  # no text
    assert "(untitled)" in md and "[?]" in md
