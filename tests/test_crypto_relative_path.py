"""Key initialization accepts the same relative paths as other file operations."""
import os

import pytest

from iris import crypto as C


@pytest.mark.parametrize('path', ['key.txt', './key.txt', 'nested/key.txt'])
def test_generate_key_at_relative_path(tmp_path, monkeypatch, path):
    monkeypatch.chdir(tmp_path)
    public = C.generate_key(path)
    assert public.startswith('age1')
    keyfile = tmp_path / path
    assert keyfile.is_file()
    assert C.public_key(path) == public
    if os.name != 'nt':
        assert keyfile.stat().st_mode & 0o777 == 0o600
    encrypted = C.encrypt_bytes(b'synthetic round-trip', public)
    assert C.decrypt_bytes(encrypted, path) == b'synthetic round-trip'
    original = keyfile.read_bytes()
    with pytest.raises(C.CryptoError, match='already exists'):
        C.generate_key(path)
    assert keyfile.read_bytes() == original
