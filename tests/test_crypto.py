import os, subprocess
import iris.crypto as C

KEY = "/tmp/convo-test-key.txt"

def setup_module(m):
    if os.path.exists(KEY): os.remove(KEY)
    C.generate_key(KEY)

def test_keygen_creates_600_keyfile_and_age1_pubkey():
    pub = C.public_key(KEY)
    assert pub.startswith("age1")
    assert oct(os.stat(KEY).st_mode & 0o777) == "0o600"

def test_refuses_overwrite():
    try:
        C.generate_key(KEY); assert False, "should refuse"
    except C.CryptoError: pass

def test_roundtrip():
    pub = C.public_key(KEY)
    blob = C.encrypt_bytes(b"decision: ship Friday, owner Priya", pub)
    assert b"Priya" not in blob and b"BEGIN AGE ENCRYPTED FILE" in blob
    assert C.decrypt_bytes(blob, KEY) == b"decision: ship Friday, owner Priya"

def test_wrong_key_fails():
    other = "/tmp/convo-test-key2.txt"
    if os.path.exists(other): os.remove(other)
    C.generate_key(other)
    blob = C.encrypt_bytes(b"secret", C.public_key(KEY))
    try:
        C.decrypt_bytes(blob, other); assert False, "wrong key must fail"
    except C.CryptoError: pass

def test_file_roundtrip(tmp_path):
    pub = C.public_key(KEY)
    src = tmp_path / "t.md"; src.write_text("# Notes\n- [ ] call Sam")
    enc = C.encrypt_file(str(src), pub)
    dec = tmp_path / "out.md"
    C.decrypt_file(enc, str(dec), KEY)
    assert dec.read_text() == src.read_text()
    assert "call Sam" not in open(enc).read()
