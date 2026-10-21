#!/usr/bin/env python3
"""convo - private meeting notes. ingest | sweep | list | sync | key | encrypt | read | export | share"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from convo import transcribe as T, backends, verify, store, crypto as C

STORE = os.environ.get("CONVO_STORE", "store")

def render_notes(mid, notes, segs):
    lines = [f"# Notes: {mid}", "", "## Summary", notes.get("summary", ""), "", "## Decisions"]
    for d in notes.get("decisions", []):
        lines.append(f"- {d['text']}  ")
        lines.append(f"  > \"{d['evidence']}\" [{d['at']}]")
    if notes.get("unverified_decisions"):
        lines += ["", "### Unverified (model claimed, transcript disagrees - kept for honesty)"]
        for d in notes["unverified_decisions"]:
            lines.append(f"- {d['text']} ({d['unverified_reason']})")
    lines += ["", "## Action items"]
    for a in notes.get("action_items", []):
        owner = f" ({a['owner']})" if a.get("owner") else ""
        lines.append(f"- [ ] {a['text']}{owner}  ")
        lines.append(f"  > \"{a['evidence']}\" [{a['at']}]")
    if notes.get("unverified_action_items"):
        lines += ["", "### Unverified (model claimed, transcript disagrees - kept for honesty)"]
        for a in notes["unverified_action_items"]:
            lines.append(f"- {a['text']} ({a['unverified_reason']})")
    i = notes.get("integrity", {})
    lines += ["", f"_integrity: {i.get('passed', 0)}/{i.get('checked', 0)} claims verified against transcript_"]
    return "\n".join(lines)

def cmd_ingest(audio, backend_name="ollama", title=""):
    mid = store.new_meeting(STORE, title)
    store.attach_audio(STORE, mid, audio)
    segs = T.transcribe(audio)
    tmd = T.transcript_markdown(segs)
    store.write_text(STORE, mid, "transcript.md", tmd)
    backend = backends.get_backend(backend_name)
    notes = backend.notes(tmd)
    notes = verify.verify_notes(notes, segs)
    store.write_text(STORE, mid, "notes.md", render_notes(mid, notes, segs))
    meta = json.load(open(os.path.join(STORE, mid, "meta.json")))
    meta["backend"] = backend.name
    meta["integrity"] = notes.get("integrity")
    json.dump(meta, open(os.path.join(STORE, mid, "meta.json"), "w"), indent=2)
    if os.path.exists(C.DEFAULT_KEY):
        store.encrypt_meeting(STORE, mid)
        print("encrypted: transcript.md.age, notes.md.age")
    print(f"meeting: {mid}\nbackend: {backend.name}\nintegrity: {notes['integrity']}")
    print(f"notes: {os.path.join(STORE, mid, 'notes.md')}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in ("ingest", "sweep", "list", "sync", "key", "encrypt", "read", "export", "share"):
        print(__doc__); sys.exit(1)
    if args[0] == "key":
        print("public key:", C.generate_key() if len(args) > 1 and args[1] == "init" else C.public_key())
    elif args[0] == "encrypt":
        mids = [args[1]] if len(args) > 1 else [m for m in sorted(os.listdir(STORE)) if os.path.isdir(os.path.join(STORE, m))]
        for m in mids:
            if not store.is_encrypted(STORE, m):
                print(m, "->", ", ".join(store.encrypt_meeting(STORE, m)))
    elif args[0] == "export":
        from convo import export as E
        print(E.export_meeting(STORE, args[1], args[2]))
    elif args[0] == "share":
        from convo import export as E
        print(E.share_meeting(STORE, args[1], args[2], args[3]))
    elif args[0] == "read":
        for name, text in store.decrypt_meeting(STORE, args[1]).items():
            print(f"--- {name} ---\n{text}")
    elif args[0] == "sync":
        import getpass
        server = args[args.index("--server") + 1] if "--server" in args else os.environ.get("CONVO_SYNC_SERVER", "http://127.0.0.1:8471")
        token = os.environ.get("CONVO_SYNC_TOKEN") or getpass.getpass("sync token: ")
        from convo import sync as S
        pushed = [S.push(STORE, mid, server, token)["id"] for mid in sorted(os.listdir(STORE)) if os.path.isdir(os.path.join(STORE, mid))]
        st = S.state_file(STORE)
        got = S.pull_all(STORE, server, token, st.get("last_pull", 0.0))
        st["last_pull"] = __import__("time").time(); S.save_state(STORE, st)
        print(f"pushed {len(pushed)}, pulled {len(got)}: {got}")
    elif args[0] == "ingest":
        backend = "ollama"
        if "--backend" in args:
            i = args.index("--backend"); backend = args[i + 1]; del args[i:i + 2]
        cmd_ingest(args[1], backend)
    elif args[0] == "sweep":
        for p in store.sweep(STORE): print(f"deleted {p}")
    elif args[0] == "list":
        for mid in sorted(os.listdir(STORE)): print(mid)
