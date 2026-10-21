"""Laptop mic capture -> wav (needs a real audio device: Hassan's machine).
Linux (pulse/pipewire):   python3 convo/record.py out.wav
macOS (avfoundation):     python3 convo/record.py out.wav   # auto-detected
Press Ctrl-C to stop. Add --ingest to run the full pipeline right after."""
import subprocess, sys, os, threading, time

def build_cmd(platform: str, out_wav: str) -> list[str]:
    src = (["ffmpeg", "-f", "avfoundation", "-i", ":0"] if platform == "mac"
           else ["ffmpeg", "-f", "pulse", "-i", "default"])
    return src + ["-ar", "16000", "-ac", "1", out_wav]

def default_platform() -> str:
    return "mac" if sys.platform == "darwin" else "linux"

def record(out_wav: str, platform: str = None) -> bool:
    platform = platform or default_platform()
    cmd = build_cmd(platform, out_wav)
    stop = threading.Event()
    t0 = time.time()
    def timer():
        while not stop.is_set():
            time.sleep(5)
            print(f"  recording... {int(time.time() - t0)}s (Ctrl-C to stop)", flush=True)
    threading.Thread(target=timer, daemon=True).start()
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
    if not os.path.exists(out_wav) or os.path.getsize(out_wav) < 1000:
        hint = ("No audio captured. Linux: check `pactl list sources short`. "
                "macOS: grant Terminal mic access in System Settings > Privacy & Security > Microphone.")
        print(hint, file=sys.stderr)
        return False
    print(f"saved {out_wav} ({os.path.getsize(out_wav) // 1024} KB, {int(time.time() - t0)}s)")
    return True

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else "meeting.wav"
    if record(out):
        if "--ingest" in sys.argv:
            from convo import cli
            cli.cmd_ingest(out)
