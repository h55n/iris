import pytest
from iris.lang import classify

@pytest.mark.parametrize("text,want", [
    ("We should ship the release on Monday", "en"),
    ("The to-do list is done", "en"),
    ("kal meeting hai kya", "hinglish"),
    ("yaar ye kaam bahut zyada ho gaya", "hinglish"),
    ("Please send the deck, phir hum call karenge", "hinglish"),
    ("नमस्ते आप कैसे हैं", "hi"),
    ("कल का deadline fix karna hai please", "hinglish"),
    ("OK", "en"),
    ("", "en"),
    ("12:30 sharp", "en"),
])
def test_classify(text, want):
    assert classify(text) == want

def test_ambiguous_words_alone_are_not_hinglish():
    assert classify("go to the sir") == "en"
