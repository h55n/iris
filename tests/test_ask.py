from iris import ask

def test_terms_drop_stopwords():
    assert ask.terms("What did we decide about the retention?") == ["decide", "retention"]

def test_terms_keep_non_english_words():
    assert "बैठक" in ask.terms("कल की बैठक")

def _meeting(tmp_path, title, transcript):
    import json, time
    from iris import store as S
    mid = S.new_meeting(str(tmp_path), title)
    S.write_text(str(tmp_path), mid, "transcript.md", transcript)
    return mid

def test_ask_quotes_the_exact_line_with_timestamp(tmp_path):
    mid = _meeting(tmp_path, "Planning", "[00:05] Speaker 1: retention stays seven days\n[00:09] Speaker 2: lunch is at one")
    hits = ask.ask(str(tmp_path), "How long is retention?")
    assert hits[0]["meeting"] == mid and hits[0]["at"] == "00:05"
    assert hits[0]["quote"] == "Speaker 1: retention stays seven days"

def test_ask_returns_nothing_for_unrelated_question(tmp_path):
    _meeting(tmp_path, "Planning", "[00:05] Speaker 1: retention stays seven days")
    assert ask.ask(str(tmp_path), "what is the budget for catering") == []

def test_ask_ranks_fuller_match_first(tmp_path):
    _meeting(tmp_path, "A", "[00:01] Speaker 1: sync is encrypted\n[00:02] Speaker 2: sync relay holds no plaintext")
    hits = ask.ask(str(tmp_path), "does the sync relay hold plaintext")
    assert hits[0]["at"] == "00:02"
