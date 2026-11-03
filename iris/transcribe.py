"""Transcription via whisper.cpp CLI. Same engine that ships to phone/laptop."""
import json, os, re, shlex, shutil, subprocess, sys, tempfile

WHISPER_CLI = os.environ.get("IRIS_WHISPER_CLI", "vendor/whisper.cpp/build/bin/whisper-cli")
MODEL = os.environ.get("IRIS_WHISPER_MODEL", "models/ggml-tiny.en.bin")
VAD_MODEL = os.environ.get("IRIS_VAD_MODEL", "models/ggml-silero-v6.2.0.bin")
EXTRA_FLAGS = os.environ.get("IRIS_WHISPER_EXTRA_FLAGS", "")  # e.g. "-mc 0 --suppress-nst" (benchmark experiments)

# Opt-in "careful" decode: -mc 0 (no context carry between 30s windows).
# Held-out confirmation on 30-min slices never used for tuning (TESTED.md,
# 2026-10-25): Hindi -15.0, Tamil -2.8, code-switched Hindi-English -13.0 WER
# vs standard decode; Spanish regressed +0.6 and English was neutral, so
# careful applies only where a held-out win was measured. Cost: ~2-5x wall
# time on CI hardware. The default decode is unchanged.
CAREFUL_FLAGS = ["-mc", "0"]
CAREFUL_LANGS = {"hi", "ta", "auto"}  # "auto" = the multilingual / code-switched path

# Bengali is unsupported: ggml-small and large-v3-turbo both emit the wrong
# script for Bengali audio (measured 100% WER, TESTED.md). Refuse it loudly
# rather than return a wrong-script transcript that looks like a result.
UNSUPPORTED_LANGS = {"bn"}

class UnsupportedLanguageError(RuntimeError):
    pass

def careful_requested(careful: bool | None) -> bool:
    """Explicit argument wins; otherwise the IRIS_WHISPER_CAREFUL env var."""
    if careful is not None:
        return careful
    return os.environ.get("IRIS_WHISPER_CAREFUL", "").strip().lower() in ("1", "true", "yes", "on")

def to_wav16k(src: str) -> str:
    """Any audio/video -> 16kHz mono wav (whisper.cpp input contract)."""
    if not os.path.exists(src):
        raise FileNotFoundError(f"audio not found: {src}")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not installed (apt install ffmpeg / brew install ffmpeg)")
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    r = subprocess.run(["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out],
                       capture_output=True)
    if r.returncode != 0:
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:]
        raise RuntimeError(f"ffmpeg could not convert {src}: {'; '.join(tail) or 'unknown error'}")
    return out

def transcribe(audio_path: str, model: str = MODEL, language: str = "en", raw_out: str | None = None,
               careful: bool | None = None) -> list[dict]:
    """Returns [{'start': float, 'end': float, 'text': str}] segments.
    careful=True (or IRIS_WHISPER_CAREFUL=1) opts into the measured -mc 0 decode;
    it is applied only for languages with a held-out win (CAREFUL_LANGS)."""
    if language in UNSUPPORTED_LANGS:
        raise UnsupportedLanguageError(
            f"language '{language}' is not supported: whisper emits the wrong script for it "
            f"(measured 100% WER at every tested model size - see TESTED.md)")
    if not os.path.exists(model):
        raise FileNotFoundError(
            f"whisper model not found: {model} - download it from "
            f"hf.co/ggerganov/whisper.cpp (see README), or set IRIS_WHISPER_MODEL")
    wav = to_wav16k(audio_path)
    out_prefix = tempfile.NamedTemporaryFile(delete=False).name
    cmd = [WHISPER_CLI, "-m", model, "-f", wav, "-l", language, "-oj", "-of", out_prefix]
    if os.path.exists(VAD_MODEL):
        cmd += ["--vad", "-vm", VAD_MODEL, "-vmsd", "10"]
    if EXTRA_FLAGS:
        cmd += shlex.split(EXTRA_FLAGS)
    if careful_requested(careful):
        if language in CAREFUL_LANGS:
            if "-mc" not in cmd:
                cmd += CAREFUL_FLAGS
        else:
            print(f"note: careful decode has no measured win for '{language}' "
                  f"(Spanish regressed slightly, English neutral - TESTED.md); standard decode used",
                  file=sys.stderr)
    subprocess.run(cmd, check=True, capture_output=True)
    raw_path = out_prefix + ".json"
    raw = open(raw_path, "rb").read()
    if raw_out:
        shutil.copyfile(raw_path, raw_out)  # preserve exact whisper bytes as evidence
    # whisper can emit byte sequences that are not valid UTF-8 (e.g. Devanagari
    # byte-level tokens with no completing neighbor); decode tolerantly so the
    # pipeline survives. Replacement chars (U+FFFD) stay in the text and count
    # as WER errors - they mark real model output defects, not clean accuracy.
    data = json.loads(raw.decode("utf-8", errors="replace"))
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
        from iris.lang import classify
        tag = s.get("lang") or "en"
        if classify(s["text"]) == "hinglish":
            tag = "hinglish"  # mixed Hindi/English beats whisper's single-language guess
        lang = f"<{tag}> " if tag != "en" else ""
        lines.append(f"[{mmss(s['start'])}] {who}{lang}{s['text']}")
    return "\n".join(lines)


def transcribe_multilingual(audio_path: str, model: str = None, careful: bool | None = None) -> list[dict]:
    """Mixed-language meetings (Hinglish): segment with the multilingual
    model, then detect language per segment. A base.en pass drops non-English
    speech entirely (tested: Hindi turns vanished from segmentation), so this
    path always uses a multilingual model."""
    model = model or os.environ.get("IRIS_WHISPER_MULTILINGUAL_MODEL", "models/ggml-small.bin")
    segs = transcribe(audio_path, model=model, language="auto", careful=careful)
    segs = detect_segment_languages(audio_path, segs, model)
    if any(s.get("lang") in UNSUPPORTED_LANGS for s in segs):
        print("warning: Bengali speech detected - Bengali is UNSUPPORTED (whisper writes the "
              "wrong script, measured 100% WER). This transcript is unreliable; see TESTED.md.",
              file=sys.stderr)
    return segs

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
