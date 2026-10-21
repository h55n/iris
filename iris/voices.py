"""Voice enrollment: teach Iris who a speaker is from a short sample clip,
so transcripts say 'Priya:' instead of 'Speaker 2:'.

Fully local: the same ERes2Net embedding model used for diarization.
Voiceprints live at ~/.iris/voices/<name>.npy - they are embeddings
(192-d floats), not audio, and never leave the machine.

  iris enroll Priya priya-sample.wav     # 5-15s of clean speech is enough
  iris ingest meeting.wav --diarize      # known voices appear as names
"""
from __future__ import annotations
import os, wave
import numpy as np

EMB_MODEL = os.environ.get("IRIS_EMB_MODEL", "models/eres2net_en.onnx")
VOICES_DIR = os.path.expanduser(os.environ.get("IRIS_VOICES", "~/.iris/voices"))
MATCH_THRESHOLD = float(os.environ.get("IRIS_VOICE_THRESHOLD", "0.5"))

def available() -> bool:
    return os.path.exists(EMB_MODEL)

def _extractor():
    import sherpa_onnx
    return sherpa_onnx.SpeakerEmbeddingExtractor(
        sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=EMB_MODEL))

def _read_wav16(path: str) -> np.ndarray:
    with wave.open(path) as w:
        if w.getframerate() != 16000 or w.getnchannels() != 1:
            raise ValueError("needs 16kHz mono wav - run transcribe.to_wav16k first")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

def embedding_of(wav_path: str) -> np.ndarray:
    """Mean-pooled speaker embedding of a 16kHz mono wav."""
    ex = _extractor()
    samples = _read_wav16(wav_path)
    stream = ex.create_stream()
    stream.accept_waveform(16000, samples)
    stream.input_finished()
    v = np.array(ex.compute(stream), dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v

def enroll(name: str, wav_path: str, voices_dir: str = VOICES_DIR) -> str:
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("name must be alphanumeric (- and _ allowed)")
    os.makedirs(voices_dir, exist_ok=True)
    dest = os.path.join(voices_dir, name + ".npy")
    np.save(dest, embedding_of(wav_path))
    return dest

def load_voices(voices_dir: str = VOICES_DIR) -> dict[str, np.ndarray]:
    out = {}
    if os.path.isdir(voices_dir):
        for f in sorted(os.listdir(voices_dir)):
            if f.endswith(".npy"):
                out[f[:-4]] = np.load(os.path.join(voices_dir, f))
    return out

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0

def match(emb: np.ndarray, voices: dict[str, np.ndarray],
          threshold: float = MATCH_THRESHOLD) -> tuple[str | None, float]:
    """Best enrolled voice for an embedding, or None under threshold."""
    best, best_score = None, 0.0
    for name, v in voices.items():
        s = cosine(emb, v)
        if s > best_score:
            best, best_score = name, s
    return (best, best_score) if best_score >= threshold else (None, best_score)

def cluster_embeddings(wav_path: str, dia_segs: list[dict]) -> dict[int, np.ndarray]:
    """One embedding per diarized speaker cluster, computed over that
    cluster's audio (up to ~20s from its longest segments)."""
    samples = _read_wav16(wav_path)
    ex = _extractor()
    out = {}
    for spk in sorted({d["speaker"] for d in dia_segs}):
        parts = sorted((d for d in dia_segs if d["speaker"] == spk),
                       key=lambda d: d["end"] - d["start"], reverse=True)
        buf, total = [], 0
        for d in parts:
            a, b = int(d["start"] * 16000), int(d["end"] * 16000)
            seg = samples[a:b]
            if len(seg) == 0: continue
            buf.append(seg); total += len(seg)
            if total > 20 * 16000: break
        if not buf: continue
        stream = ex.create_stream()
        stream.accept_waveform(16000, np.concatenate(buf))
        stream.input_finished()
        v = np.array(ex.compute(stream), dtype=np.float32)
        n = np.linalg.norm(v)
        out[spk] = v / n if n else v
    return out

def name_clusters(wav_path: str, dia_segs: list[dict], voices_dir: str = VOICES_DIR,
                  threshold: float = MATCH_THRESHOLD) -> dict[int, str]:
    """Map diarization cluster ids to enrolled names where confident."""
    voices = load_voices(voices_dir)
    if not voices:
        return {}
    names = {}
    for spk, emb in cluster_embeddings(wav_path, dia_segs).items():
        name, score = match(emb, voices, threshold)
        if name:
            names[spk] = name
    return names
