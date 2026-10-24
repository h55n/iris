"""Regression: whisper.cpp can emit invalid UTF-8 in segment text (observed on
FLEURS hi_in and MUCS Hindi-English CI legs, UnicodeDecodeError at json.load).
transcribe() must survive, mark defects as U+FFFD, and preserve raw bytes."""
import json, subprocess
from iris import transcribe as T

# Real byte pattern class from the CI failure: a 3-byte Devanagari lead byte
# (0xE0) followed by an ASCII byte - an invalid continuation.
FIXTURE = (b'{"systeminfo":"x","transcription":[{"timestamps":{"from":"00:00:00,000","to":"00:00:02,000"},'
           b'"offsets":{"from":0,"to":2000},"text":"\xe0\xa4\xa8\xe0\xa4\xae\xe0\xa4\xb8 \xe0\xa5\x8dok \xe0\xa4\xa4\xe0\xa5\x87 \xe0bad"},'
           b'{"timestamps":{"from":"00:00:02,000","to":"00:00:04,000"},"offsets":{"from":2000,"to":4000},'
           b'"text":"\xe0\xa4\xb8\xe0\xa5\x81\xe0\xa4\xa8\xe0\xa4\xbe"}]}')
# text[0] = "नमस" + " ्ok" + " ते" + raw byte 0xE0 + "bad" (0xE0 is a lone lead byte -> U+FFFD)
# text[1] = "सुना" (fully valid; valid speech text must survive untouched)

def test_invalid_utf8_segment_decodes_with_replacement_and_raw_preserved(tmp_path, monkeypatch):
    model = tmp_path / "fake-model.bin"; model.write_bytes(b"x")
    audio = tmp_path / "a.wav"; audio.write_bytes(b"RIFF")

    def fake_run(cmd, **kw):
        if "-oj" in cmd:  # whisper-cli: write the defective fixture
            open(cmd[cmd.index("-of") + 1] + ".json", "wb").write(FIXTURE)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(T.subprocess, "run", fake_run)
    monkeypatch.setattr(T.os.path, "exists", lambda p: True)

    raw_out = tmp_path / "raw.json"
    segs = T.transcribe(str(audio), model=str(model), language="hi", raw_out=str(raw_out))

    assert len(segs) == 2
    assert "\ufffd" in segs[0]["text"]            # defective byte marked, not crashed
    assert sum(s["text"].count("\ufffd") for s in segs) == 1
    assert "\ufffd" not in segs[1]["text"]        # valid Devanagari text untouched
    assert raw_out.read_bytes() == FIXTURE        # exact raw bytes preserved as evidence

def test_valid_utf8_unchanged(tmp_path, monkeypatch):
    model = tmp_path / "m.bin"; model.write_bytes(b"x")
    audio = tmp_path / "a.wav"; audio.write_bytes(b"RIFF")

    def fake_run(cmd, **kw):
        if "-oj" in cmd:
            open(cmd[cmd.index("-of") + 1] + ".json", "wb").write(
                '{"transcription":[{"offsets":{"from":0,"to":1000},"text":"hello नमस्ते"}]}'.encode())
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(T.subprocess, "run", fake_run)
    monkeypatch.setattr(T.os.path, "exists", lambda p: True)
    segs = T.transcribe(str(audio), model=str(model), language="hi")
    assert segs[0]["text"] == "hello नमस्ते"
