import sys
from convo import record

def test_linux_cmd():
    c = record.build_cmd("linux", "o.wav")
    assert c[:4] == ["ffmpeg", "-f", "pulse", "-i"] and "16000" in c

def test_mac_cmd():
    c = record.build_cmd("mac", "o.wav")
    assert "avfoundation" in c

def test_platform_autodetect():
    assert record.default_platform() == ("mac" if sys.platform == "darwin" else "linux")
