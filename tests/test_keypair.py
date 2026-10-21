import os
from iris import crypto as C

K = "/tmp/convo-export2-key.txt"

def test_export_secret_line():
    if not os.path.exists(K): C.generate_key(K)
    s = C.export_secret(K)
    assert s.startswith("AGE-SECRET-KEY-1")

def test_qr_renders():
    if not os.path.exists(K): C.generate_key(K)
    art = C.export_qr(K)
    assert len(art) > 200 and "\n" in art
