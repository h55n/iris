"""Library: pins, project folders, blank notes and free editing.
Everything lives next to the meetings (store/_folders.json + two meta.json
keys), so it syncs and encrypts like the rest and needs no database."""
import json, os, re, time, uuid
from iris import store as S

FOLDERS = "_folders.json"

def _folders_path(store_dir): return os.path.join(store_dir, FOLDERS)

def list_folders(store_dir: str) -> list[dict]:
    try:
        data = json.load(open(_folders_path(store_dir)))
        return [f for f in data if isinstance(f, dict) and f.get("id") and f.get("name")]
    except (OSError, json.JSONDecodeError):
        return []

def _save_folders(store_dir, folders):
    os.makedirs(store_dir, exist_ok=True)
    tmp = _folders_path(store_dir) + ".tmp"
    json.dump(folders, open(tmp, "w"), indent=2)
    os.replace(tmp, _folders_path(store_dir))

def create_folder(store_dir: str, name: str) -> dict:
    name = " ".join(name.split())[:60]
    if not name:
        raise ValueError("folder needs a name")
    folders = list_folders(store_dir)
    f = {"id": "f-" + uuid.uuid4().hex[:6], "name": name, "created": time.time()}
    _save_folders(store_dir, folders + [f])
    return f

def rename_folder(store_dir: str, fid: str, name: str) -> bool:
    name = " ".join(name.split())[:60]
    folders = list_folders(store_dir)
    hit = [f for f in folders if f["id"] == fid]
    if not hit or not name:
        return False
    hit[0]["name"] = name
    _save_folders(store_dir, folders)
    return True

def delete_folder(store_dir: str, fid: str) -> bool:
    """Removes the folder only. Its notes are kept and move back to 'All notes'."""
    folders = list_folders(store_dir)
    if not any(f["id"] == fid for f in folders):
        return False
    for mid in S.list_meetings(store_dir):
        meta = S._load_meta(store_dir, mid)
        if meta.get("folder") == fid:
            meta.pop("folder", None)
            S._save_meta(store_dir, mid, meta)
    _save_folders(store_dir, [f for f in folders if f["id"] != fid])
    return True

def move(store_dir: str, mid: str, fid: str | None) -> None:
    meta = S._load_meta(store_dir, mid)
    if fid and not any(f["id"] == fid for f in list_folders(store_dir)):
        raise ValueError("no such folder")
    if fid: meta["folder"] = fid
    else: meta.pop("folder", None)
    S._save_meta(store_dir, mid, meta)

def set_pinned(store_dir: str, mid: str, pinned: bool) -> None:
    meta = S._load_meta(store_dir, mid)
    if pinned: meta["pinned"] = True
    else: meta.pop("pinned", None)
    S._save_meta(store_dir, mid, meta)

def new_note(store_dir: str, title: str = "", folder: str | None = None) -> str:
    """A blank note you type into (no recording)."""
    mid = S.new_meeting(store_dir, title or "Untitled")
    S.write_text(store_dir, mid, "notes.md", "")
    meta = S._load_meta(store_dir, mid)
    meta["kind"] = "note"
    if folder and any(f["id"] == folder for f in list_folders(store_dir)):
        meta["folder"] = folder
    S._save_meta(store_dir, mid, meta)
    return mid

def save_notes(store_dir: str, mid: str, text: str, key_path: str | None = None) -> None:
    """Replace notes.md. Encrypted meetings stay encrypted: the new text is
    sealed to the same key and no plaintext file is left behind."""
    from iris import crypto as C
    text = text.replace("\r\n", "\n")
    d = os.path.join(store_dir, mid)
    if S.is_encrypted(store_dir, mid):
        enc = os.path.join(d, "notes.md.age")
        pub = C.public_key(key_path or C.DEFAULT_KEY)
        plain = os.path.join(d, "notes.md")
        open(plain, "w").write(text)
        try:
            C.encrypt_file(plain, pub)
        finally:
            if os.path.exists(plain): os.remove(plain)
    else:
        S.write_text(store_dir, mid, "notes.md", text)
    meta = S._load_meta(store_dir, mid)
    meta["edited"] = time.time()
    S._save_meta(store_dir, mid, meta)

def tidy_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()[:120]
