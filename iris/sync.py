"""Sync client: push local meetings to / pull remote meetings from the sync server.
Audio files are explicitly excluded - they never leave their device.
Push is incremental: a per-meeting content hash in .sync-state.json skips
meetings that have not changed since the last push."""
import hashlib, json, os, time, urllib.request

def _req(url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data,
        headers={"X-Iris-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def _bundle(store_dir, mid):
    d = os.path.join(store_dir, mid)
    b = {"id": mid}
    for name, key in (("meta.json", "meta"), ("transcript.md", "transcript"), ("notes.md", "notes"),
                      ("transcript.md.age", "transcript_age"), ("notes.md.age", "notes_age")):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            b[key] = (json.load(open(p)) if name.endswith(".json") else open(p).read())
    return b  # audio deliberately absent

def bundle_hash(store_dir, mid):
    return hashlib.sha256(json.dumps(_bundle(store_dir, mid), sort_keys=True).encode()).hexdigest()

def push(store_dir, mid, server, token):
    return _req(f"{server}/push/{mid}", token, _bundle(store_dir, mid))

def push_changed(store_dir, server, token):
    """Push only meetings whose content changed since the last push."""
    st = state_file(store_dir)
    hashes = st.get("push_hashes", {})
    pushed, skipped = [], []
    for mid in sorted(os.listdir(store_dir)):
        if not os.path.isdir(os.path.join(store_dir, mid)):
            continue
        try:
            h = bundle_hash(store_dir, mid)
        except (OSError, ValueError):
            skipped.append(mid); continue  # unreadable meeting: skip, never push garbage
        if hashes.get(mid) == h:
            skipped.append(mid); continue
        push(store_dir, mid, server, token)
        hashes[mid] = h
        pushed.append(mid)
    st["push_hashes"] = hashes
    save_state(store_dir, st)
    return pushed, skipped

def push_folders(store_dir, server, token):
    """Project folders ride along as one tiny bundle. True when something was sent."""
    from iris import library as L
    folders = L.list_folders(store_dir)
    st = state_file(store_dir)
    h = hashlib.sha256(json.dumps(folders, sort_keys=True).encode()).hexdigest()
    if st.get("folders_hash") == h:
        return False
    _req(f"{server}/push/_folders", token, {"id": "_folders", "folders": folders})
    st["folders_hash"] = h
    save_state(store_dir, st)
    return True

def merge_folders(store_dir, remote):
    """Union by id. A folder renamed on one device keeps the local name;
    folders never get deleted by a sync."""
    from iris import library as L
    local = L.list_folders(store_dir)
    ids = {f["id"] for f in local}
    add = [f for f in remote if isinstance(f, dict) and f.get("id") and f.get("name") and f["id"] not in ids]
    if add:
        L._save_folders(store_dir, local + add)
    return len(add)

def _newer_locally(d, remote_meta):
    try:
        local = json.load(open(os.path.join(d, "meta.json")))
    except (OSError, json.JSONDecodeError):
        return False
    return local.get("edited", 0) > (remote_meta or {}).get("edited", 0)

def pull_all(store_dir, server, token, since=0.0):
    got = []
    for m in _req(f"{server}/list?since={since}", token)["meetings"]:
        b = _req(f"{server}/pull/{m['id']}", token)
        if m["id"] == "_folders":
            merge_folders(store_dir, b.get("folders", []))
            continue
        d = os.path.join(store_dir, m["id"])
        if _newer_locally(d, b.get("meta")):
            continue  # your edit here is newer than the copy on the relay
        os.makedirs(d, exist_ok=True)
        if "meta" in b: json.dump(b["meta"], open(os.path.join(d, "meta.json"), "w"), indent=2)
        for key, name in (("transcript", "transcript.md"), ("notes", "notes.md"),
                          ("transcript_age", "transcript.md.age"), ("notes_age", "notes.md.age")):
            if key in b: open(os.path.join(d, name), "w").write(b[key])
        got.append(m["id"])
    return got

def state_file(store_dir):
    p = os.path.join(store_dir, ".sync-state.json")
    return json.load(open(p)) if os.path.isfile(p) else {"last_pull": 0.0}

def save_state(store_dir, st):
    json.dump(st, open(os.path.join(store_dir, ".sync-state.json"), "w"))
