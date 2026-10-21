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
