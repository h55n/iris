from iris import verify

SEGS = [{"start": 0, "end": 5, "text": "Priya owns the sync server."}]

def _notes(item):
    return {"summary": "", "decisions": [], "action_items": [item]}

def test_empty_evidence_demoted():
    out = verify.verify_notes(_notes({"text": "x", "owner": "", "evidence": "", "at": "00:01"}), SEGS)
    assert out["unverified_action_items"]

def test_owner_case_insensitive():
    out = verify.verify_notes(_notes({"text": "own sync", "owner": "PRIYA", "evidence": "Priya owns the sync server", "at": "00:01"}), SEGS)
    assert out["integrity"]["passed"] == 1

def test_timestamp_within_tolerance_passes():
    out = verify.verify_notes(_notes({"text": "own sync", "owner": "Priya", "evidence": "Priya owns the sync server", "at": "00:20"}), SEGS)
    assert out["integrity"]["passed"] == 1  # 20s from seg end 5s, within 30s tolerance

def test_timestamp_far_outside_demoted():
    out = verify.verify_notes(_notes({"text": "own sync", "owner": "Priya", "evidence": "Priya owns the sync server", "at": "05:00"}), SEGS)
    assert out["unverified_action_items"]

def test_clause_trimmed_quote_accepted():
    out = verify.verify_notes(_notes({"text": "own sync", "owner": "Priya", "evidence": "owns the sync server", "at": "00:01"}), SEGS)
    assert out["integrity"]["passed"] == 1

def test_garbage_timestamp_format_demoted():
    out = verify.verify_notes(_notes({"text": "x", "owner": "", "evidence": "Priya owns the sync server", "at": "soon"}), SEGS)
    assert out["unverified_action_items"]
