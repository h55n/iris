"""Laptop mic capture -> wav (UNTESTED here: sandbox has no audio device).
Linux (pulse/pipewire):   python3 convo/record.py out.wav
macOS (avfoundation):     python3 convo/record.py out.wav --mac
Press Ctrl-C to stop; then `python3 convo/cli.py ingest out.wav`."""
import subprocess, sys, os

def record(out_wav, platform="linux"):
    cmd = (["ffmpeg", "-f", "avfoundation", "-i", ":0"] if platform == "mac"
           else ["ffmpeg", "-f", "pulse", "-i", "default"])
    cmd += ["-ar", "16000", "-ac", "1", out_wav]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    return os.path.exists(out_wav)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "meeting.wav"
    record(out, "mac" if "--mac" in sys.argv else "linux")
