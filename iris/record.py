"""Laptop mic capture -> wav (needs a real audio device: Hassan's machine).
Linux (pulse/pipewire):   python3 iris/record.py out.wav
macOS (avfoundation):     python3 iris/record.py out.wav   # auto-detected
Windows (DirectShow):     python iris/record.py out.wav    # auto-detected
Press Ctrl-C to stop. Add --ingest to run the full pipeline right after.
--list-devices prints capture device names (Windows dshow needs the exact
friendly name; Linux/mac have usable defaults) and exits."""
import subprocess, sys, os, re, threading, time

def build_cmd(platform: str, out_wav: str, device: str = None) -> list[str]:
    if platform == "mac":
        src = ["ffmpeg", "-f", "avfoundation", "-i", f":{device or '0'}"]
    elif platform == "windows":
        # dshow wants the friendly name from --list-devices; "default" is only
        # a last-ditch guess, record() enumerates real devices first.
        src = ["ffmpeg", "-f", "dshow", "-i", f"audio={device or 'default'}"]
    else:
        src = ["ffmpeg", "-f", "pulse", "-i", device or "default"]
    return src + ["-ar", "16000", "-ac", "1", out_wav]

def default_platform() -> str:
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"

def list_devices(platform: str = None) -> list[str]:
    """Audio capture device names. Only Windows (dshow) needs enumeration;
    Linux/mac return [] - their defaults work."""
    platform = platform or default_platform()
    if platform != "windows":
        return []
    proc = subprocess.run(
        ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
        capture_output=True, text=True)
    return parse_dshow_devices(proc.stderr)

def parse_dshow_devices(ffmpeg_stderr: str) -> list[str]:
    """Parse ffmpeg -list_devices dshow output into audio device names.

    Handles both layouts ffmpeg has shipped:
      legacy:  'DirectShow audio devices' section header, then '"Name"' lines
               (each followed by an 'Alternative name "@device_..."' line)
      ffmpeg7: '"Name" (audio)' / '"Name" (video)' markers per line
    """
    names, section = [], None
    for line in ffmpeg_stderr.splitlines():
        if "DirectShow video devices" in line:
            section = "video"; continue
        if "DirectShow audio devices" in line:
            section = "audio"; continue
        m = re.search(r'"([^"]+)"', line)
        if not m:
            continue
        name = m.group(1)
        if name.startswith("@device_"):
            continue  # alternative-name alias line, not a friendly name
        if "(audio)" in line or "(video)" in line:      # ffmpeg 7+ markers
            if "(audio)" in line:
                names.append(name)
        elif section == "audio":                         # legacy sectioned layout
            names.append(name)
    return names

def record(out_wav: str, platform: str = None, device: str = None) -> bool:
    platform = platform or default_platform()
    if platform == "windows" and device is None:
        devices = list_devices("windows")
        if not devices:
            print("No Windows audio capture device found. Run with --list-devices "
                  "to check ffmpeg's dshow listing, and check Settings > Privacy "
                  "& security > Microphone is on for desktop apps.", file=sys.stderr)
            return False
        device = devices[0]
        print(f"Windows mic: using '{device}' (override with --device)")
    cmd = build_cmd(platform, out_wav, device)
    stop = threading.Event()
    t0 = time.time()
    def timer():
        while not stop.is_set():
            time.sleep(5)
            print(f"  recording... {int(time.time() - t0)}s (Ctrl-C to stop)", flush=True)
    threading.Thread(target=timer, daemon=True).start()
    print("REMINDER: tell everyone on the call you're recording. India allows one-party")
    print("consent (you being present counts), but announcing is the product's behavior.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
    if not os.path.exists(out_wav) or os.path.getsize(out_wav) < 1000:
        hint = {
            "linux": "No audio captured. Linux: check `pactl list sources short`.",
            "mac": "No audio captured. macOS: grant Terminal mic access in System Settings > Privacy & Security > Microphone.",
            "windows": "No audio captured. Windows: check Settings > Privacy & security > Microphone, "
                       "and run with --list-devices to pick the right --device name.",
        }[platform]
        print(hint, file=sys.stderr)
        return False
    print(f"saved {out_wav} ({os.path.getsize(out_wav) // 1024} KB, {int(time.time() - t0)}s)")
    return True

if __name__ == "__main__":
    if "--list-devices" in sys.argv:
        devs = list_devices()
        if default_platform() == "windows":
            print("\n".join(devs) if devs else "(no audio capture devices found)")
        else:
            print(f"{default_platform()}: device listing not needed, default input works")
        sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else "meeting.wav"
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else None
    if record(out, device=dev):
        if "--ingest" in sys.argv:
            from iris import cli
            cli.cmd_ingest(out)
