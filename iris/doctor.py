"""iris doctor - one command to check a machine is ready to run everything.
Prints OK / MISSING per dependency with the fix. Exit 1 if anything core is missing."""
from iris import crypto as C
import os, shutil, subprocess, sys

def _ok(name, yes, fix=""):
    print(f"  {'OK ' if yes else 'MISSING'}  {name}" + (f"  -> {fix}" if not yes and fix else ""))
    return yes

def main():
    print("iris doctor")
    core = True
    core &= _ok("ffmpeg", shutil.which("ffmpeg") is not None, "apt install ffmpeg / brew install ffmpeg")
    core &= _ok("whisper-cli", os.path.exists("vendor/whisper.cpp/build/bin/whisper-cli"),
                "build whisper.cpp into vendor/ (see README)")
    core &= _ok("whisper model (base.en)", os.path.exists("models/ggml-base.en.bin"),
                "download ggml-base.en.bin from hf.co/ggerganov/whisper.cpp")
    _ok("silero VAD model", os.path.exists("models/ggml-silero-v6.2.0.bin"),
        "download ggml-silero-v6.2.0.bin from hf.co/ggml-org/whisper-vad")
    _ok("multilingual model (small, for Hindi)", os.path.exists("models/ggml-small.bin"),
        "download ggml-small.bin - needed for non-English meetings")
    _ok("encryption key", os.path.exists(C.DEFAULT_KEY),
        "python3 iris/cli.py key init")
    _ok("diarization models", os.path.exists("models/pyannote-seg-3-0.onnx") and os.path.exists("models/eres2net_en.onnx"),
        "models/get-diarize-models.sh")
    _ok("sherpa-onnx (speaker labels)", _importable("sherpa_onnx"), "pip install sherpa-onnx")
    _ok("qrcode (key pairing QR)", _importable("qrcode"), "pip install qrcode")
    _ok("numpy (voiceprints)", _importable("numpy"), "pip install numpy")
    _ok("ollama (local notes)", _http_up("http://127.0.0.1:11434"),
        "install ollama + `ollama pull gemma3:4b`, or use --backend ultramarine")
    try:
        from iris import voices as V
        names = sorted(V.load_voices()) if V.available() else []
        if names:
            print(f"  voices enrolled: {', '.join(names)}")
    except Exception:
        pass
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        print(f"  repo   {r.stdout.strip()}")
    except Exception:
        pass
    if not core:
        print("core dependencies missing"); sys.exit(1)
    print("ready")

def _importable(mod):
    try:
        __import__(mod); return True
    except Exception:
        return False

def _http_up(url):
    import urllib.request
    try:
        urllib.request.urlopen(url, timeout=2); return True
    except Exception:
        return False

if __name__ == "__main__":
    main()
