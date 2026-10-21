"""Local store. Transcripts+notes kept; recordings auto-deleted after 7 days.
Encryption at rest lands in v1.5 (age). Layout:
  store/<meeting-id>/audio.*   (deleted by sweep after RETENTION_DAYS)
  store/<meeting-id>/transcript.md
  store/<meeting-id>/notes.md
  store/<meeting-id>/meta.json"""
import json, os, shutil, time, uuid

RETENTION_DAYS = 7

def new_meeting(store_dir: str, title: str = "") -> str:
    mid = time.strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:6]
    os.makedirs(os.path.join(store_dir, mid), exist_ok=True)
    meta = {"id": mid, "title": title or mid, "created": time.time(), "audio_files": []}
    _save_meta(store_dir, mid, meta)
    return mid

def attach_audio(store_dir: str, mid: str, audio_path: str) -> str:
    dest = os.path.join(store_dir, mid, "audio" + os.path.splitext(audio_path)[1].lower())
    shutil.copyfile(audio_path, dest)
    meta = _load_meta(store_dir, mid)
    meta["audio_files"].append(os.path.basename(dest))
    _save_meta(store_dir, mid, meta)
    return dest

def write_text(store_dir: str, mid: str, name: str, text: str):
    with open(os.path.join(store_dir, mid, name), "w") as f:
        f.write(text)

def sweep(store_dir: str, now: float = None) -> list[str]:
    """Delete recordings older than RETENTION_DAYS; transcripts and notes stay."""
    now = now or time.time()
    deleted = []
    for mid in os.listdir(store_dir):
        d = os.path.join(store_dir, mid)
        meta_path = os.path.join(d, "meta.json")
        if not os.path.isfile(meta_path): continue
        meta = json.load(open(meta_path))
        if now - meta["created"] < RETENTION_DAYS * 86400: continue
        for af in meta.get("audio_files", []):
            p = os.path.join(d, af)
            if os.path.exists(p):
                os.remove(p); deleted.append(p)
        meta["audio_deleted_at"] = now
        meta["audio_files"] = []
        _save_meta(store_dir, mid, meta)
    return deleted

def _load_meta(store_dir, mid):
    return json.load(open(os.path.join(store_dir, mid, "meta.json")))

def _save_meta(store_dir, mid, meta):
    with open(os.path.join(store_dir, mid, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


"""Encryption wiring (age). When the user has a key (~/.convo/key.txt),
transcript.md and notes.md are stored as .age ciphertext only - the relay
and the disk never hold plaintext. Audio is untouched (deleted by sweep)."""
from convo import crypto as C

PLAINTEXT_FILES = ("transcript.md", "notes.md")

def encrypt_meeting(store_dir: str, mid: str, key_path: str = C.DEFAULT_KEY) -> list[str]:
    pub = C.public_key(key_path)
    done = []
    d = os.path.join(store_dir, mid)
    for name in PLAINTEXT_FILES:
        src = os.path.join(d, name)
        if os.path.exists(src):
            C.encrypt_file(src, pub)
            os.remove(src)
            done.append(name + ".age")
    meta = _load_meta(store_dir, mid)
    meta["encrypted"] = True
    _save_meta(store_dir, mid, meta)
    return done

def decrypt_meeting(store_dir: str, mid: str, key_path: str = C.DEFAULT_KEY) -> dict:
    out = {}
    d = os.path.join(store_dir, mid)
    for name in PLAINTEXT_FILES:
        enc = os.path.join(d, name + ".age")
        if os.path.exists(enc):
            out[name] = C.decrypt_bytes(open(enc, "rb").read(), key_path).decode()
    return out

def is_encrypted(store_dir: str, mid: str) -> bool:
    return bool(_load_meta(store_dir, mid).get("encrypted"))


def search(store_dir: str, query: str, key_path: str = None) -> list[dict]:
    """Full-text search over transcripts + notes (decrypts with local key as
    needed). Returns [{'meeting': mid, 'file': name, 'line': str}]."""
    import re
    hits = []
    rx = re.compile(re.escape(query), re.I)
    for mid in sorted(os.listdir(store_dir)):
        d = os.path.join(store_dir, mid)
        if not os.path.isfile(os.path.join(d, "meta.json")): continue
        if is_encrypted(store_dir, mid):
            texts = decrypt_meeting(store_dir, mid, key_path or C.DEFAULT_KEY)
        else:
            texts = {n: open(os.path.join(d, n)).read()
                     for n in PLAINTEXT_FILES if os.path.exists(os.path.join(d, n))}
        for name, text in texts.items():
            for line in text.splitlines():
                if rx.search(line):
                    hits.append({"meeting": mid, "file": name, "line": line.strip()})
    return hits
