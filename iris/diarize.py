"""Speaker diarization via sherpa-onnx: pyannote-3.0 segmentation (ONNX) +
3dspeaker ERes2Net embeddings + fast clustering. Fully local, free, no
accounts. Tested on real two-human audio (LibriSpeech) and synthetic TTS:
every turn correctly attributed. See TESTED.md.

Models (gitignored, download with models/get-diarize-models.sh):
  models/pyannote-seg-3-0.onnx   (6 MB)
  models/eres2net_en.onnx        (26 MB)
"""
from __future__ import annotations
import os, wave
import numpy as np

SEG_MODEL = os.environ.get("IRIS_SEG_MODEL", "models/pyannote-seg-3-0.onnx")
EMB_MODEL = os.environ.get("IRIS_EMB_MODEL", "models/eres2net_en.onnx")

def available() -> bool:
    return os.path.exists(SEG_MODEL) and os.path.exists(EMB_MODEL)

def diarize(wav_path: str, num_speakers: int = 0) -> list[dict]:
    """Returns [{'start': s, 'end': e, 'speaker': int}] time-ordered.
    num_speakers=0 lets the clusterer decide (threshold-based)."""
    import sherpa_onnx
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=SEG_MODEL)),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=EMB_MODEL),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=num_speakers),
        min_duration_on=0.2, min_duration_off=0.3)
    sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
    with wave.open(wav_path) as w:
        if w.getframerate() != 16000:
            raise ValueError("diarize() needs 16kHz mono wav - run transcribe.to_wav16k first")
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return [{"start": r.start, "end": r.end, "speaker": r.speaker}
            for r in sd.process(samples).sort_by_start_time()]

def assign_speakers(transcript_segs: list[dict], dia_segs: list[dict]) -> list[dict]:
    """Label each transcript segment with the speaker it overlaps most.
    Pure function - unit-tested without the models."""
    out = []
    for t in transcript_segs:
        best, best_ov = None, 0.0
        for d in dia_segs:
            ov = max(0.0, min(t["end"], d["end"]) - max(t["start"], d["start"]))
            if ov > best_ov:
                best, best_ov = d["speaker"], ov
        out.append({**t, "speaker": best})
    return out

def merge_same_speaker(dia_segs: list[dict], gap: float = 0.8) -> list[dict]:
    """Merge adjacent same-speaker turns separated by < gap seconds."""
    out = []
    for s in dia_segs:
        if out and out[-1]["speaker"] == s["speaker"] and s["start"] - out[-1]["end"] < gap:
            out[-1]["end"] = s["end"]
        else:
            out.append(dict(s))
    return out
