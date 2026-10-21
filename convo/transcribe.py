"""Transcription via whisper.cpp CLI. Same engine that ships to phone/laptop."""
import json, os, re, subprocess, tempfile

WHISPER_CLI = os.environ.get("CONVO_WHISPER_CLI", "vendor/whisper.cpp/build/bin/whisper-cli")
MODEL = os.environ.get("CONVO_WHISPER_MODEL", "models/ggml-tiny.en.bin")
VAD_MODEL = os.environ.get("CONVO_VAD_MODEL", "models/ggml-silero-v6.2.0.bin")

def to_wav16k(src: str) -> str:
    """Any audio/video -> 16kHz mono wav (whisper.cpp input contract)."""
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out],
                   check=True, capture_output=True)
    return out

def transcribe(audio_path: str, model: str = MODEL, language: str = "en") -> list[dict]:
    """Returns [{'start': float, 'end': float, 'text': str}] segments."""
    wav = to_wav16k(audio_path)
    out_prefix = tempfile.NamedTemporaryFile(delete=False).name
    cmd = [WHISPER_CLI, "-m", model, "-f", wav, "-l", language, "-oj", "-of", out_prefix]
    if os.path.exists(VAD_MODEL):
        cmd += ["--vad", "-vm", VAD_MODEL, "-vmsd", "10"]
    subprocess.run(cmd, check=True, capture_output=True)
    with open(out_prefix + ".json") as f:
        data = json.load(f)
    segs = []
    for s in data["transcription"]:
        segs.append({"start": _ts(s["offsets"]["from"]), "end": _ts(s["offsets"]["to"]),
                     "text": s["text"].strip()})
    return segs

def _ts(ms: int) -> float:
    return round(ms / 1000.0, 2)

def mmss(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def transcript_markdown(segs: list[dict]) -> str:
    return "\n".join(f"[{mmss(s['start'])}] {s['text']}" for s in segs)
