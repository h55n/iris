from iris.mascot import mascot

def test_all_moods_render_valid_svg():
    for m in ("happy", "sleep", "celebrate"):
        s = mascot(80, m)
        assert s.startswith("<svg") and s.endswith("</svg>") and 'width="80"' in s

def test_bloom_uses_theme_accent():
    assert "var(--accent)" in mascot(80, "celebrate")
    assert "var(--accent)" not in mascot(80, "happy")

def test_no_character_features():
    for m in ("happy", "sleep", "celebrate"):
        assert "<circle" not in mascot(80, m).replace('<circle cx="101" cy="70"', "")  # only the flower centre

def test_unknown_mood_falls_back_to_sprout():
    assert mascot(50, "weird") == mascot(50, "happy")
