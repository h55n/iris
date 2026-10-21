"""Encryption at rest for the meeting store, using age (X25519).

Threat model: transcripts and notes sit on disk and move between the
user's own devices. A lost laptop or a compromised sync relay must not
expose them. Each device holds the same user keypair (private key file
chmod 600, generated once, copied via QR/manual - never over the wire).
The sync relay only ever sees .age ciphertext.

Key file: ~/.convo/key.txt  (age secret key; the public key line inside
is the "device fingerprint" users compare when pairing devices.)
"""
from __future__ import annotations
import os, subprocess, sys

AGE = os.environ.get("CONVO_AGE", os.path.join(os.path.dirname(__file__), "..", "vendor", "age"))
AGE_KEYGEN = os.environ.get("CONVO_AGE_KEYGEN", os.path.join(os.path.dirname(__file__), "..", "vendor", "age-keygen"))
DEFAULT_KEY = os.path.expanduser(os.environ.get("CONVO_KEY", "~/.convo/key.txt"))

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

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pubkey"
    if cmd == "init":
        print("public key:", generate_key())
    elif cmd == "pubkey":
        print(public_key())
