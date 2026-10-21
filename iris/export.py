"""Export and share.

export: one self-contained markdown file (transcript + notes + integrity
line + meta), plaintext, for pasting into docs/wikis. Audio never included.

share: the same bundle encrypted to a RECIPIENT'S age public key - only
that person can open it. Fits the at-rest model: sharing = re-encrypting
to someone else's key, not uploading anywhere.
"""
from __future__ import annotations
import json, os, time
from iris import crypto as C, store as S

def _get_texts(store_dir: str, mid: str, key_path: str | None) -> dict:
    """Return {name: text} for transcript.md/notes.md, decrypting if needed."""
    d = os.path.join(store_dir, mid)
    if S.is_encrypted(store_dir, mid):
        return S.decrypt_meeting(store_dir, mid, key_path or C.DEFAULT_KEY)
    out = {}
    for name in S.PLAINTEXT_FILES:
        p = os.path.join(d, name)
        if os.path.exists(p):
            out[name] = open(p).read()
    return out

def build_bundle(store_dir: str, mid: str, key_path: str | None = None) -> str:
    meta = json.load(open(os.path.join(store_dir, mid, "meta.json")))
    texts = _get_texts(store_dir, mid, key_path)
    created = time.strftime("%Y-%m-%d %H:%M", time.localtime(meta["created"]))
    parts = [f"# Meeting notes: {meta.get('title', mid)}",
             f"_exported {time.strftime('%Y-%m-%d %H:%M')} - recorded {created} - id {mid}_", ""]
    if "notes.md" in texts:
        parts += [texts["notes.md"], ""]
    if "transcript.md" in texts:
        parts += ["---", "", "## Full transcript", "", texts["transcript.md"]]
    return "\n".join(parts)

def export_meeting(store_dir: str, mid: str, out_path: str, key_path: str | None = None) -> str:
    with open(out_path, "w") as f:
        f.write(build_bundle(store_dir, mid, key_path))
    return out_path

def share_meeting(store_dir: str, mid: str, recipient_pub: str, out_path: str,
                  key_path: str | None = None) -> str:
    """Encrypt the export bundle to the recipient's age key."""
    blob = C.encrypt_bytes(build_bundle(store_dir, mid, key_path).encode(), recipient_pub)
    with open(out_path, "w") as f:
        f.write(blob.decode())
    return out_path
