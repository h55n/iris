"""Iris Cloud link for the local app: remember where to sync, and run a sync.
Only notes go up by default. Audio never does. The token sits in
<store>/.cloud.json with owner-only permissions."""
import json, os, time

DEFAULT_SERVER = "https://iris-cloud-one.vercel.app/sync"
_FILE = ".cloud.json"

def _path(store_dir): return os.path.join(store_dir, _FILE)

def load(store_dir):
    try:
        return json.load(open(_path(store_dir)))
    except (OSError, ValueError):
        return {}

def save(store_dir, server, token, transcripts=False):
    server = (server or DEFAULT_SERVER).strip().rstrip("/")
    if not server.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise ValueError("server must be https (plain http only for localhost)")
    cfg = load(store_dir)
    cfg.update({"server": server, "transcripts": bool(transcripts)})
    if token: cfg["token"] = token.strip()
    _write(store_dir, cfg)

def _write(store_dir, cfg):
    p = _path(store_dir)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(cfg, f)
    os.chmod(p, 0o600)

def forget(store_dir):
    try: os.remove(_path(store_dir))
    except OSError: pass

def status(store_dir):
    cfg = load(store_dir)
    return {"linked": bool(cfg.get("token")), "server": cfg.get("server", DEFAULT_SERVER),
            "transcripts": bool(cfg.get("transcripts")), "last": cfg.get("last_sync")}

def sync_now(store_dir):
    """Push changed notes, then pull edits made elsewhere. Returns a one-line result."""
    from iris import sync as S
    cfg = load(store_dir)
    if not cfg.get("token"): raise RuntimeError("not linked yet")
    server, token = cfg.get("server", DEFAULT_SERVER), cfg["token"]
    notes_only = not cfg.get("transcripts")
    pushed, skipped = S.push_changed(store_dir, server, token, notes_only=notes_only)
    S.push_folders(store_dir, server, token)
    st = S.state_file(store_dir)
    got = S.pull_all(store_dir, server, token, st.get("last_pull", 0.0))
    st["last_pull"] = time.time(); S.save_state(store_dir, st)
    cfg["last_sync"] = st["last_pull"]
    _write(store_dir, cfg)
    return {"pushed": len(pushed), "unchanged": len(skipped), "pulled": len(got)}
