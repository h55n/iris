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

def _save_text(store_dir: str, mid: str, name: str, text: str, key_path: str | None = None) -> None:
    """Write notes.md or transcript.md. Encrypted meetings stay encrypted: the
    new text is sealed to the same key and no plaintext file is left behind."""
    from iris import crypto as C
    d = os.path.join(store_dir, mid)
    if S.is_encrypted(store_dir, mid):
        pub = C.public_key(key_path or C.DEFAULT_KEY)
        plain = os.path.join(d, name)
        open(plain, "w").write(text)
        try:
            C.encrypt_file(plain, pub)
        finally:
            if os.path.exists(plain): os.remove(plain)
    else:
        S.write_text(store_dir, mid, name, text)
    meta = S._load_meta(store_dir, mid)
    meta["edited"] = time.time()
    S._save_meta(store_dir, mid, meta)

def save_notes(store_dir: str, mid: str, text: str, key_path: str | None = None) -> None:
    _save_text(store_dir, mid, "notes.md", text.replace("\r\n", "\n"), key_path)

SPEAKER_NAME = re.compile(r"^[A-Za-z\u0900-\u097F][\w\u0900-\u097F -]{0,29}$")

def rename_speaker(store_dir: str, mid: str, old: str, new: str, key_path: str | None = None) -> int:
    """Turn 'Speaker 2:' into 'Priya:' across the transcript and notes.
    Returns how many transcript lines changed. Only exact speaker labels at
    the start of a line are touched, never words inside what was said."""
    from iris import export as E
    new = " ".join(new.split())
    if not SPEAKER_NAME.match(new):
        raise ValueError("speaker names are letters, numbers, spaces and - only (max 30)")
    texts = E._get_texts(store_dir, mid, key_path)
    tr = texts.get("transcript.md", "")
    pat = re.compile(r"^(\[\d\d:\d\d(?::\d\d)?\] )" + re.escape(old) + r": ", re.M)
    new_tr, n = pat.subn(lambda m: f"{m.group(1)}{new}: ", tr)
    if n:
        _save_text(store_dir, mid, "transcript.md", new_tr, key_path)
        notes = texts.get("notes.md")
        if notes:
            npat = re.compile(r"(?<![\w])" + re.escape(old) + r"(?=[:\s,.)])")
            if npat.search(notes):
                _save_text(store_dir, mid, "notes.md", npat.sub(new, notes), key_path)
    return n

def tidy_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()[:120]


def reorder_folders(store_dir: str, ids: list[str]) -> bool:
    """Put folders in the given order. Unknown ids are ignored; folders not
    listed keep their relative order after the listed ones."""
    folders = list_folders(store_dir)
    by_id = {f["id"]: f for f in folders}
    first = [by_id[i] for i in dict.fromkeys(ids) if i in by_id]
    rest = [f for f in folders if f["id"] not in {x["id"] for x in first}]
    new = first + rest
    if [f["id"] for f in new] == [f["id"] for f in folders]:
        return False
    _save_folders(store_dir, new)
    return True

def reorder_notes(store_dir: str, ids: list[str]) -> int:
    """Manual order for notes (pinned list, a folder). Stores meta['order'] =
    position, so it survives sync. Returns how many notes changed."""
    n = 0
    real = set(S.list_meetings(store_dir))
    for pos, mid in enumerate(i for i in dict.fromkeys(ids) if i in real):
        meta = S._load_meta(store_dir, mid)
        if meta.get("order") != pos:
            meta["order"] = pos
            S._save_meta(store_dir, mid, meta)
            n += 1
    return n

def order_key(meta: dict):
    """Manually ordered notes first (by order), the rest newest-first."""
    return (0, meta.get("order", 0), 0) if "order" in meta else (1, 0, -meta.get("created", 0))


TRASH = ".trash"
TRASH_DAYS = 30

def trash_dir(store_dir): return os.path.join(store_dir, TRASH)

def trash_note(store_dir: str, mid: str) -> bool:
    """Soft delete: the folder moves to .trash and can be restored for 30 days."""
    import shutil
    src = os.path.join(store_dir, mid)
    if "/" in mid or ".." in mid or not os.path.isfile(os.path.join(src, "meta.json")):
        return False
    meta = S._load_meta(store_dir, mid)
    meta["trashed_at"] = time.time()
    S._save_meta(store_dir, mid, meta)
    os.makedirs(trash_dir(store_dir), exist_ok=True)
    shutil.move(src, os.path.join(trash_dir(store_dir), mid))
    return True

def list_trash(store_dir: str) -> list[dict]:
    out = []
    td = trash_dir(store_dir)
    for mid in sorted(os.listdir(td)) if os.path.isdir(td) else []:
        try:
            meta = json.load(open(os.path.join(td, mid, "meta.json")))
        except (OSError, json.JSONDecodeError):
            continue
        out.append({"id": mid, "title": meta.get("title", mid), "trashed_at": meta.get("trashed_at", 0)})
    return sorted(out, key=lambda t: -t["trashed_at"])

def restore_note(store_dir: str, mid: str) -> bool:
    import shutil
    src = os.path.join(trash_dir(store_dir), mid)
    dst = os.path.join(store_dir, mid)
    if "/" in mid or ".." in mid or not os.path.isdir(src) or os.path.exists(dst):
        return False
    shutil.move(src, dst)
    meta = S._load_meta(store_dir, mid)
    meta.pop("trashed_at", None)
    S._save_meta(store_dir, mid, meta)
    return True

def purge_trash(store_dir: str, now: float | None = None, older_than_days: float = TRASH_DAYS) -> int:
    """Permanently remove trashed notes older than the window (0 = everything)."""
    import shutil
    now = now or time.time()
    n = 0
    for t in list_trash(store_dir):
        if now - t["trashed_at"] >= older_than_days * 86400:
            shutil.rmtree(os.path.join(trash_dir(store_dir), t["id"]), ignore_errors=True)
            n += 1
    return n


def duplicate_note(store_dir: str, mid: str, key_path: str | None = None) -> str:
    """Copy a note's text (not audio or transcript) into a new note in the same
    folder. A copy of an encrypted note is encrypted the same way."""
    from iris import export as E
    meta = S._load_meta(store_dir, mid)
    texts = E._get_texts(store_dir, mid, key_path)
    new = new_note(store_dir, f"Copy of {meta.get('title', mid)}"[:120], meta.get("folder"))
    save_notes(store_dir, new, texts.get("notes.md", ""))
    if meta.get("encrypted"):
        S.encrypt_meeting(store_dir, new, key_path)
    return new

def word_count(text: str) -> int:
    return len(re.findall(r"[\w\u0900-\u097F']+", text))
