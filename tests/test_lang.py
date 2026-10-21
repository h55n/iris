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

def test_transcript_markdown_tags_hinglish_even_when_whisper_says_en():
    from iris.transcribe import transcript_markdown
    md = transcript_markdown([{"start": 1, "end": 3, "text": "kal meeting hai kya", "lang": "en", "speaker": 0},
                              {"start": 4, "end": 6, "text": "Sounds good to me", "lang": "en", "speaker": 1},
                              {"start": 7, "end": 9, "text": "नमस्ते", "lang": "hi", "speaker": 0}])
    lines = md.splitlines()
    assert lines[0] == "[00:01] Speaker 1: <hinglish> kal meeting hai kya"
    assert lines[1] == "[00:04] Speaker 2: Sounds good to me"
    assert lines[2] == "[00:07] Speaker 1: <hi> नमस्ते"
