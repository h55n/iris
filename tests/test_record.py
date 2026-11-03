import sys
from iris import record

def test_linux_cmd():
    c = record.build_cmd("linux", "o.wav")
    assert c[:4] == ["ffmpeg", "-f", "pulse", "-i"] and "16000" in c

def test_mac_cmd():
    c = record.build_cmd("mac", "o.wav")
    assert "avfoundation" in c

def test_platform_autodetect():
    if sys.platform == "darwin":
        assert record.default_platform() == "mac"
    elif sys.platform.startswith("win"):
        assert record.default_platform() == "windows"
    else:
        assert record.default_platform() == "linux"

def test_device_override_linux():
    c = record.build_cmd("linux", "o.wav", "alsa_output.usb")
    assert "alsa_output.usb" in c

def test_device_override_mac():
    c = record.build_cmd("mac", "o.wav", "1")
    assert ":1" in c

def test_default_device():
    assert "default" in record.build_cmd("linux", "o.wav")
    assert ":0" in record.build_cmd("mac", "o.wav")

def test_windows_cmd():
    c = record.build_cmd("windows", "o.wav", "Microphone (Realtek(R) Audio)")
    assert c[:4] == ["ffmpeg", "-f", "dshow", "-i"]
    assert "audio=Microphone (Realtek(R) Audio)" in c
    assert "16000" in c

def test_windows_cmd_default_is_last_ditch():
    c = record.build_cmd("windows", "o.wav")
    assert "audio=default" in c

LEGACY = """[dshow @ 000001ab] DirectShow video devices (some may be both video and audio devices)
[dshow @ 000001ab]  "Integrated Camera"
[dshow @ 000001ab]     Alternative name "@device_pnp_\\\\?\\usb#vid"
[dshow @ 000001ab] DirectShow audio devices
[dshow @ 000001ab]  "Microphone (Realtek(R) Audio)"
[dshow @ 000001ab]     Alternative name "@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\\wave"
[dshow @ 000001ab]  "Stereo Mix (Realtek(R) Audio)"
[dshow @ 000001ab]     Alternative name "@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\\wave2"
"""

MODERN = """[in#0 @ 000002b1] "Integrated Camera" (video)
[in#0 @ 000002b1]   Alternative name "@device_pnp_\\\\?\\usb#vid"
[in#0 @ 000002b1] "Microphone (Realtek(R) Audio)" (audio)
[in#0 @ 000002b1]   Alternative name "@device_cm_{33D9A762}\\wave"
[in#0 @ 000002b1] "CABLE Output (VB-Audio Virtual Cable)" (audio)
"""

def test_parse_dshow_legacy():
    devs = record.parse_dshow_devices(LEGACY)
    assert devs == ["Microphone (Realtek(R) Audio)", "Stereo Mix (Realtek(R) Audio)"]

def test_parse_dshow_ffmpeg7_markers():
    devs = record.parse_dshow_devices(MODERN)
    assert devs == ["Microphone (Realtek(R) Audio)", "CABLE Output (VB-Audio Virtual Cable)"]

def test_parse_dshow_empty():
    assert record.parse_dshow_devices("ffmpeg version 7.1\nno devices here") == []

def test_list_devices_non_windows_skips_ffmpeg():
    assert record.list_devices("linux") == []
    assert record.list_devices("mac") == []
