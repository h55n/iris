from iris import ask

def test_terms_drop_stopwords():
    assert ask.terms("What did we decide about the retention?") == ["decide", "retention"]

def test_terms_keep_non_english_words():
    assert "बैठक" in ask.terms("कल की बैठक")
