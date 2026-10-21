import numpy as np
from iris import voices as V

def test_cosine_identical():
    a = np.random.rand(192).astype(np.float32)
    assert abs(V.cosine(a, a) - 1.0) < 1e-6

def test_cosine_orthogonal():
    a = np.zeros(192, dtype=np.float32); a[0] = 1
    b = np.zeros(192, dtype=np.float32); b[1] = 1
    assert abs(V.cosine(a, b)) < 1e-6

def test_match_picks_nearest():
    rng = np.random.default_rng(7)
    target = rng.random(192).astype(np.float32)
    near = target + rng.normal(0, 0.01, 192).astype(np.float32)
    far = rng.random(192).astype(np.float32)
    voices = {"Priya": near, "Hassan": far}
    name, score = V.match(near, voices, threshold=0.5)
    assert name == "Priya" and score > 0.9

def test_match_below_threshold_returns_none():
    rng = np.random.default_rng(3)
    emb = rng.random(192).astype(np.float32)
    voices = {"Someone": rng.random(192).astype(np.float32)}
    name, score = V.match(emb, voices, threshold=0.99)
    assert name is None

def test_match_empty_voices():
    assert V.match(np.ones(192, dtype=np.float32), {}, threshold=0.5) == (None, 0.0)

def test_enroll_rejects_bad_names(tmp_path):
    import pytest
    for bad in ("", "a b", "../x", "na;me"):
        with pytest.raises(ValueError):
            V.enroll(bad, "/nonexistent.wav", str(tmp_path))

def test_enroll_rejects_short_audio(tmp_path):
    import pytest, wave, struct
    wav = str(tmp_path / "blip.wav")
    with wave.open(wav, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(struct.pack("<1600h", *([0] * 1600)))  # 0.1s
    with pytest.raises(ValueError, match="too short"):
        V.enroll("Priya", wav, str(tmp_path / "voices"))
