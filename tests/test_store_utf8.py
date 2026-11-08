"""The stored text format must not depend on the machine's locale."""
import builtins

import pytest

from iris import export as E, store as S


@pytest.fixture(params=["native", "cp1252"])
def legacy_locale(request, monkeypatch):
    if request.param == "native":
        return
    def locale_open(file, mode="r", *args, **kwargs):
        if "b" not in mode and not args and kwargs.get("encoding") is None:
            kwargs["encoding"] = "cp1252"
        return builtins.open(file, mode, *args, **kwargs)

    monkeypatch.setattr(S, "open", locale_open, raising=False)
    monkeypatch.setattr(E, "open", locale_open, raising=False)


def test_write_text_is_utf8_with_non_utf8_locale(tmp_path, legacy_locale):
    mid = S.new_meeting(str(tmp_path), "Synthetic meeting")
    text = "नमस्ते தமிழ் café"
    S.write_text(str(tmp_path), mid, "notes.md", text)
    assert (tmp_path / mid / "notes.md").read_bytes() == text.encode("utf-8")


def test_search_reads_utf8_with_non_utf8_locale(tmp_path, legacy_locale):
    mid = S.new_meeting(str(tmp_path), "Synthetic meeting")
    text = "Action: नमस्ते café"
    (tmp_path / mid / "notes.md").write_bytes(text.encode("utf-8"))
    hits = S.search(str(tmp_path), "नमस्ते")
    assert hits == [{"meeting": mid, "file": "notes.md", "line": text}]


def test_export_reads_and_writes_utf8_with_non_utf8_locale(tmp_path, legacy_locale):
    store = tmp_path / "meetings"
    mid = S.new_meeting(str(store), "Synthetic meeting")
    text = "नमस्ते தமிழ் café"
    for name in S.PLAINTEXT_FILES:
        (store / mid / name).write_bytes(text.encode("utf-8"))
    destination = tmp_path / "export.md"
    E.export_meeting(str(store), mid, str(destination))
    exported = destination.read_bytes().decode("utf-8")
    assert exported.count(text) == 2

