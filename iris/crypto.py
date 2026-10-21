"""Encryption at rest for the meeting store, using age (X25519).

Threat model: transcripts and notes sit on disk and move between the
user's own devices. A lost laptop or a compromised sync relay must not
expose them. Each device holds the same user keypair (private key file
chmod 600, generated once, copied via QR/manual - never over the wire).
The sync relay only ever sees .age ciphertext.

Key file: ~/.iris/key.txt  (age secret key; the public key line inside
is the "device fingerprint" users compare when pairing devices.)
"""
from __future__ import annotations
import os, subprocess, sys

AGE = os.environ.get("IRIS_AGE", os.path.join(os.path.dirname(__file__), "..", "vendor", "age"))
AGE_KEYGEN = os.environ.get("IRIS_AGE_KEYGEN", os.path.join(os.path.dirname(__file__), "..", "vendor", "age-keygen"))
def _legacy(new_path, old_path):
    return new_path if os.path.exists(new_path) or not os.path.exists(old_path) else old_path

DEFAULT_KEY = _legacy(os.path.expanduser(os.environ.get("IRIS_KEY", "~/.iris/key.txt")),
                      os.path.expanduser("~/.convo/key.txt"))

class CryptoError(RuntimeError):
    pass

def _run(cmd, data: bytes) -> bytes:
    p = subprocess.run(cmd, input=data, capture_output=True)
    if p.returncode != 0:
        raise CryptoError(p.stderr.decode(errors="replace").strip() or f"{cmd[0]} failed")
    return p.stdout

def generate_key(path: str = DEFAULT_KEY) -> str:
    """Create key file, return the public key. Refuses to overwrite."""
    if os.path.exists(path):
        raise CryptoError(f"key already exists: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = subprocess.run([AGE_KEYGEN, "-o", path], capture_output=True, text=True)
    if out.returncode != 0:
        raise CryptoError(out.stderr.strip())
    os.chmod(path, 0o600)
    return public_key(path)

def public_key(path: str = DEFAULT_KEY) -> str:
    # "Public key: age1..." line is printed by age-keygen at creation; recover
    # from the secret via `age-keygen -y` (no passphrase prompt for plain keys).
    p = subprocess.run([AGE_KEYGEN, "-y", path], capture_output=True, text=True)
    if p.returncode != 0:
        raise CryptoError(p.stderr.strip())
    return p.stdout.strip()

def encrypt_bytes(data: bytes, recipient_pub: str) -> bytes:
    return _run([AGE, "-r", recipient_pub, "-a"], data)   # -a: ASCII armor

def decrypt_bytes(blob: bytes, key_path: str = DEFAULT_KEY) -> bytes:
    return _run([AGE, "-d", "-i", key_path], blob)

def encrypt_file(src: str, recipient_pub: str, dst: str | None = None) -> str:
    dst = dst or (src + ".age")
    with open(src, "rb") as f:
        blob = encrypt_bytes(f.read(), recipient_pub)
    with open(dst, "w") as f:
        f.write(blob.decode())
    return dst

def decrypt_file(src: str, dst: str, key_path: str = DEFAULT_KEY) -> str:
    with open(src, "rb") as f:
        data = decrypt_bytes(f.read(), key_path)
    with open(dst, "wb") as f:
        f.write(data)
    return dst

def export_secret(path: str = DEFAULT_KEY) -> str:
    """The AGE-SECRET-KEY-1... line, for pairing another device. Keep it as
    private as the key file itself."""
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("AGE-SECRET-KEY-"):
                    return line.strip()
    except FileNotFoundError:
        raise CryptoError(f"no key at {path} - run `iris key init` first") from None
    raise CryptoError(f"no secret key line in {path}")

def export_qr(path: str = DEFAULT_KEY) -> str:
    """ASCII QR of the secret key for phone pairing (scan with any scanner,
    paste into the Iris app). Rendered locally - the key never leaves."""
    import io, qrcode
    qr = qrcode.QRCode(border=1)
    qr.add_data(export_secret(path))
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()

def key_info(path: str = DEFAULT_KEY) -> str:
    import time
    st = os.stat(path)
    return (f"key file: {path}\n"
            f"created: {time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_ctime))}\n"
            f"public: {public_key(path)}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pubkey"
    if cmd == "init":
        print("public key:", generate_key())
    elif cmd == "pubkey":
        print(public_key())
    elif cmd == "export":
        print(export_secret())
    elif cmd == "qr":
        print(export_qr())
    elif cmd == "info":
        print(key_info())
