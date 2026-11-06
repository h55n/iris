import os
from iris import store as S, crypto as C, export as E

KEY = "/tmp/iris-export-key.txt"; RKEY = "/tmp/iris-export-rkey.txt"
STORE = "/tmp/iris-export-store"

def setup_module(m):
    os.system(f"rm -rf {STORE} {KEY} {RKEY} /tmp/exp*.md*")
    os.makedirs(STORE)
    for k in (KEY, RKEY):
        if not os.path.exists(k): C.generate_key(k)
    mid = S.new_meeting(STORE, "sync demo")
    S.write_text(STORE, mid, "transcript.md", "[00:01] ship Friday")
    S.write_text(STORE, mid, "notes.md", "## Decisions\n- ship Friday")
    S.encrypt_meeting(STORE, mid, KEY)

def test_bundle_contains_notes_transcript_and_title():
    mid = sorted(os.listdir(STORE))[0]
    b = E.build_bundle(STORE, mid, KEY)
    assert "sync demo" in b and "ship Friday" in b and "Full transcript" in b

def test_export_plaintext():
    mid = sorted(os.listdir(STORE))[0]
    p = E.export_meeting(STORE, mid, "/tmp/exp1.md", KEY)
    assert "ship Friday" in open(p).read()

def test_share_only_recipient_can_open():
    mid = sorted(os.listdir(STORE))[0]
    p = E.share_meeting(STORE, mid, C.public_key(RKEY), "/tmp/exp2.md.age", KEY)
    blob = open(p, "rb").read()
    assert b"ship Friday" not in blob
    assert "ship Friday" in C.decrypt_bytes(blob, RKEY).decode()
    try:
        C.decrypt_bytes(blob, KEY); assert False, "owner key must NOT open it"
    except C.CryptoError: pass

def test_share_rejects_non_age_key(tmp_path):
    from iris import export as E, crypto as C
    import pytest
    with pytest.raises(C.CryptoError, match="not an age public key"):
        E.share_meeting("/tmp/iris-export-test", "whatever", "ssh-ed25519 AAAA...", str(tmp_path / "o.age"))


def test_failed_export_preserves_existing_destination(tmp_path, monkeypatch):
    import pytest
    destination = tmp_path / 'existing.md'
    destination.write_text('previous good export', encoding='utf-8')
    def fail(*args):
        raise C.CryptoError('test key cannot open this meeting')
    monkeypatch.setattr(E, 'build_bundle', fail)
    with pytest.raises(C.CryptoError):
        E.export_meeting(str(tmp_path), 'synthetic', str(destination))
    assert destination.read_text(encoding='utf-8') == 'previous good export'


def test_failed_export_does_not_create_empty_destination(tmp_path, monkeypatch):
    import pytest
    destination = tmp_path / 'not-created.md'
    def fail(*args):
        raise FileNotFoundError('test meeting metadata missing')
    monkeypatch.setattr(E, 'build_bundle', fail)
    with pytest.raises(FileNotFoundError):
        E.export_meeting(str(tmp_path), 'synthetic', str(destination))
    assert not destination.exists()


def test_successful_export_writes_the_complete_bundle(tmp_path, monkeypatch):
    destination = tmp_path / 'export.md'
    monkeypatch.setattr(E, 'build_bundle', lambda *args: '# Synthetic meeting\nComplete notes')
    result = E.export_meeting(str(tmp_path), 'synthetic', str(destination))
    assert result == str(destination)
    assert destination.read_text() == '# Synthetic meeting\nComplete notes'


def test_real_missing_meeting_preserves_existing_export(tmp_path):
    import pytest
    destination = tmp_path / 'existing.md'
    destination.write_text('previous good export')
    with pytest.raises(FileNotFoundError):
        E.export_meeting(str(tmp_path), 'missing-meeting', str(destination))
    assert destination.read_text() == 'previous good export'


def test_real_wrong_key_preserves_existing_export(tmp_path):
    import pytest
    store = str(tmp_path / 'meetings')
    mid = S.new_meeting(store, 'Synthetic encryption test')
    S.write_text(store, mid, 'notes.md', '# Synthetic notes only')
    S.encrypt_meeting(store, mid, KEY)
    destination = tmp_path / 'existing.md'
    destination.write_text('previous good export')
    with pytest.raises(C.CryptoError):
        E.export_meeting(store, mid, str(destination), RKEY)
    assert destination.read_text() == 'previous good export'
