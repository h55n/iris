import sys
from iris import record

def test_linux_cmd():
    c = record.build_cmd("linux", "o.wav")
    assert c[:4] == ["ffmpeg", "-f", "pulse", "-i"] and "16000" in c

def test_mac_cmd():
    c = record.build_cmd("mac", "o.wav")
    assert "avfoundation" in c

def test_platform_autodetect():
    assert record.default_platform() == ("mac" if sys.platform == "darwin" else "linux")

def test_device_override_linux():
    c = record.build_cmd("linux", "o.wav", "alsa_output.usb")
    assert "alsa_output.usb" in c

def test_device_override_mac():
    c = record.build_cmd("mac", "o.wav", "1")
    assert ":1" in c

def test_default_device():
    assert "default" in record.build_cmd("linux", "o.wav")
    assert ":0" in record.build_cmd("mac", "o.wav")
