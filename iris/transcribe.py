"""Transcription via whisper.cpp CLI. Same engine that ships to phone/laptop."""
import json, os, re, subprocess, tempfile

WHISPER_CLI = os.environ.get("IRIS_WHISPER_CLI", "vendor/whisper.cpp/build/bin/whisper-cli")
MODEL = os.environ.get("IRIS_WHISPER_MODEL", "models/ggml-tiny.en.bin")
VAD_MODEL = os.environ.get("IRIS_VAD_MODEL", "models/ggml-silero-v6.2.0.bin")

def to_wav16k(src: str) -> str:
    """Any audio/video -> 16kHz mono wav (whisper.cpp input contract)."""
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out],
                   check=True, capture_output=True)
    return out

def transcribe(audio_path: str, model: str = MODEL, language: str = "en") -> list[dict]:
    """Returns [{'start': float, 'end': float, 'text': str}] segments."""
    if not os.path.exists(model):
        raise FileNotFoundError(
            f"whisper model not found: {model} - download it from "
            f"hf.co/ggerganov/whisper.cpp (see README), or set IRIS_WHISPER_MODEL")
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

def transcript_markdown(segs: list[dict], speaker_names: dict[int, str] | None = None) -> str:
    speaker_names = speaker_names or {}
    lines = []
    for s in segs:
        spk = s.get("speaker")
        if spk is None:
            who = ""
        elif spk in speaker_names:
            who = f"{speaker_names[spk]}: "
        else:
            who = f"Speaker {spk + 1}: "
        lang = f"<{s['lang']}> " if s.get("lang") and s["lang"] != "en" else ""
        lines.append(f"[{mmss(s['start'])}] {who}{lang}{s['text']}")
    return "\n".join(lines)


def transcribe_multilingual(audio_path: str, model: str = None) -> list[dict]:
    """Mixed-language meetings (Hinglish): segment with the multilingual
    model, then detect language per segment. A base.en pass drops non-English
    speech entirely (tested: Hindi turns vanished from segmentation), so this
    path always uses a multilingual model."""
    model = model or os.environ.get("IRIS_WHISPER_MULTILINGUAL_MODEL", "models/ggml-small.bin")
    segs = transcribe(audio_path, model=model, language="auto")
    return detect_segment_languages(audio_path, segs, model)

def detect_segment_languages(audio_path: str, segs: list[dict], model: str = None) -> list[dict]:
    """Re-run whisper per segment with auto language detection. Adds seg['lang']
    and replaces seg['text'] with the detected-language transcription."""
    model = model or os.environ.get("IRIS_WHISPER_MULTILINGUAL_MODEL", "models/ggml-small.bin")
    wav = to_wav16k(audio_path)
    out = []
    for s in segs:
        dur = s["end"] - s["start"]
        if dur < 0.3:
            out.append(s); continue
        clip = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        subprocess.run(["ffmpeg", "-y", "-i", wav, "-ss", str(s["start"]), "-t", str(dur), "-c", "copy", clip],
                       check=True, capture_output=True)
        out_prefix = tempfile.NamedTemporaryFile(delete=False).name
        subprocess.run([WHISPER_CLI, "-m", model, "-f", clip, "-l", "auto", "-oj", "-of", out_prefix],
                       check=True, capture_output=True)
        with open(out_prefix + ".json") as f:
            data = json.load(f)
        text = " ".join(x["text"].strip() for x in data["transcription"]).strip()
        lang = (data.get("result") or {}).get("language", "")
        out.append({**s, "text": text or s["text"], "lang": lang})
    return out
