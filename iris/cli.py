#!/usr/bin/env python3
"""Iris - private meeting notes. ingest | sweep | list | sync | key | encrypt | read | export | share | search | ask | note | pin | unpin | folders | folder | move | enroll | voices | doctor"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iris import transcribe as T, backends, verify, store, crypto as C, render, diarize as DZ, voices as V

STORE = os.environ.get("IRIS_STORE", "store")

def cmd_ingest(audio, backend_name="ollama", title="", diarize=False, speakers=0, multilingual=False):
    mid = store.new_meeting(STORE, title)
    store.attach_audio(STORE, mid, audio)
    segs = T.transcribe_multilingual(audio) if multilingual else T.transcribe(audio)
    tmd = None
    if diarize:
        if not DZ.available():
            print("warning: diarize models missing - run models/get-diarize-models.sh "
                  "(continuing without speaker labels)", file=sys.stderr)
        else:
            dia = DZ.diarize(T.to_wav16k(audio), num_speakers=speakers)
            segs = DZ.assign_speakers(segs, dia)
            names = V.name_clusters(T.to_wav16k(audio), dia) if V.available() and V.load_voices() else {}
            print(f"speakers: {len(set(d['speaker'] for d in dia))}" + (f" ({', '.join(names.values())})" if names else ""))
            tmd = T.transcript_markdown(segs, speaker_names=names)
    if tmd is None:
        tmd = T.transcript_markdown(segs)
    store.write_text(STORE, mid, "transcript.md", tmd)
    backend = backends.get_backend(backend_name)
    notes = backend.notes(tmd)
    notes = verify.verify_notes(notes, segs)
    store.write_text(STORE, mid, "notes.md", render.render_notes(mid, notes, segs))
    meta = json.load(open(os.path.join(STORE, mid, "meta.json")))
    meta["backend"] = backend.name
    meta["integrity"] = notes.get("integrity")
    json.dump(meta, open(os.path.join(STORE, mid, "meta.json"), "w"), indent=2)
    if os.path.exists(C.DEFAULT_KEY):
        store.encrypt_meeting(STORE, mid)
        print("encrypted: transcript.md.age, notes.md.age")
    print(f"meeting: {mid}\nbackend: {backend.name}\nintegrity: {notes['integrity']}")
    print(f"notes: {os.path.join(STORE, mid, 'notes.md')}")

__version__ = "0.3.0"

def _need(args, i, what):
    if len(args) <= i:
        print(f"missing {what}", file=sys.stderr); sys.exit(1)
    return args[i]

def _need_meeting(args):
    mid = _need(args, 1, "meeting id")
    if not os.path.isdir(os.path.join(STORE, mid)):
        print(f"no such meeting: {mid}", file=sys.stderr)
        print("try: iris list", file=sys.stderr); sys.exit(1)
    return mid

def main(args):
    args = sys.argv[1:]
    if args == ["--version"]:
        print(f"iris {__version__}"); sys.exit(0)
    if not args or args[0] not in ("ingest", "sweep", "list", "sync", "key", "encrypt", "read", "export", "share", "search", "ask", "note", "pin", "unpin", "folders", "folder", "move", "enroll", "voices", "doctor"):
        print(__doc__); sys.exit(1)
    if args[0] in ("note", "pin", "unpin", "folders", "folder", "move"):
        from iris import library as Lb
        os.makedirs(STORE, exist_ok=True)
        def _folder_id(name):
            hit = [f for f in Lb.list_folders(STORE) if f["name"].lower() == name.lower() or f["id"] == name]
            if not hit:
                print(f"no such folder: {name} (try: iris folders)", file=sys.stderr); sys.exit(1)
            return hit[0]["id"]
        if args[0] == "note":
            fid = _folder_id(args[args.index("--in") + 1]) if "--in" in args else None
            title = " ".join(a for i, a in enumerate(args[1:], 1) if a != "--in" and (i < 2 or args[i - 1] != "--in"))
            print(Lb.new_note(STORE, title, fid))
        elif args[0] in ("pin", "unpin"):
            Lb.set_pinned(STORE, _need_meeting(args), args[0] == "pin")
        elif args[0] == "folders":
            for f in Lb.list_folders(STORE):
                n = sum(1 for m in store.list_meetings(STORE) if store._load_meta(STORE, m).get("folder") == f["id"])
                print(f"{f['id']}  {f['name']}  ({n})")
        elif args[0] == "folder":
            if len(args) < 3 or args[1] != "new":
                print("usage: iris folder new <name>", file=sys.stderr); sys.exit(1)
            try: print(Lb.create_folder(STORE, " ".join(args[2:]))["id"])
            except ValueError as e: print(f"error: {e}", file=sys.stderr); sys.exit(1)
        else:  # move <meeting> <folder|none>
            mid = _need_meeting(args)
            target = " ".join(args[2:])
            if not target:
                print("usage: iris move <meeting> <folder name | none>", file=sys.stderr); sys.exit(1)
            Lb.move(STORE, mid, None if target.lower() == "none" else _folder_id(target))
        return
    if args[0] == "enroll":
        if len(args) < 3 or not os.path.exists(args[2]):
            print("usage: iris enroll <name> <sample.wav>"); sys.exit(1)
        print(V.enroll(args[1], args[2]))
    elif args[0] == "voices":
        for n in V.load_voices(): print(n)
    elif args[0] == "doctor":
        from iris import doctor; doctor.main()
    elif args[0] == "key":
        if len(args) > 1 and args[1] == "init":
            try:
                print("public key:", C.generate_key())
            except C.CryptoError as e:
                print(f"error: {e}", file=sys.stderr); sys.exit(1)
        elif len(args) > 1 and args[1] == "export":
            print(C.export_secret())
        elif len(args) > 1 and args[1] == "qr":
            print(C.export_qr())
        elif len(args) > 1 and args[1] == "info":
            print(C.key_info())
        else:
            print(C.public_key())
    elif args[0] == "encrypt":
        mids = [_need_meeting(args)] if len(args) > 1 else store.list_meetings(STORE)
        for m in mids:
            if not store.is_encrypted(STORE, m):
                print(m, "->", ", ".join(store.encrypt_meeting(STORE, m)))
    elif args[0] == "search":
        if len(args) < 2:
            print("usage: iris search <words>", file=sys.stderr); sys.exit(1)
        for h in store.search(STORE, " ".join(args[1:])):
            print(f"{h['meeting']} ({h['file']}): {h['line']}")
    elif args[0] == "ask":
        if len(args) < 2:
            print("usage: iris ask <question>", file=sys.stderr); sys.exit(1)
        from iris import ask as A
        hits = A.ask(STORE, " ".join(args[1:]))
        if not hits:
            print("nothing in your meetings answers that"); return
        for h in hits:
            print(f"[{h['at']}] {h['quote']}\n    - {h['title']} ({h['meeting']})")
    elif args[0] == "export":
        from iris import export as E
        print(E.export_meeting(STORE, _need_meeting(args), _need(args, 2, "output file")))
    elif args[0] == "share":
        from iris import export as E
        print(E.share_meeting(STORE, _need_meeting(args), _need(args, 2, "their public key"), _need(args, 3, "output file")))
    elif args[0] == "read":
        for name, text in store.decrypt_meeting(STORE, _need_meeting(args)).items():
            print(f"--- {name} ---\n{text}")
    elif args[0] == "sync":
        import getpass
        server = args[args.index("--server") + 1] if "--server" in args else os.environ.get("IRIS_SYNC_SERVER", "http://127.0.0.1:8471")
        token = os.environ.get("IRIS_SYNC_TOKEN") or getpass.getpass("sync token: ")
        from iris import sync as S
        pushed, skipped = S.push_changed(STORE, server, token)
        S.push_folders(STORE, server, token)
        st = S.state_file(STORE)
        got = S.pull_all(STORE, server, token, st.get("last_pull", 0.0))
        st["last_pull"] = __import__("time").time(); S.save_state(STORE, st)
        print(f"pushed {len(pushed)} ({len(skipped)} unchanged), pulled {len(got)}: {got}")
    elif args[0] == "ingest":
        if len(args) < 2:
            print("usage: iris ingest <audio-file> [--backend ollama|ultramarine] [--diarize [--speakers N]] [--multilingual] [--title T]"); sys.exit(1)
        if not os.path.exists(args[1]):
            print(f"error: audio not found: {args[1]}", file=sys.stderr); sys.exit(1)
        backend = "ollama"
        if "--backend" in args:
            i = args.index("--backend")
            backend = args[i + 1] if i + 1 < len(args) else ""
            if backend not in ("ollama", "ultramarine"):
                print(f"unknown backend: {backend or '(missing)'} (ollama|ultramarine)", file=sys.stderr); sys.exit(1)
            del args[i:i + 2]
        dia = "--diarize" in args
        spk = 0
        if "--speakers" in args:
            i = args.index("--speakers")
            try:
                spk = int(args[i + 1])
            except (IndexError, ValueError):
                print("--speakers needs a number, e.g. --speakers 2", file=sys.stderr); sys.exit(1)
            if not 0 < spk < 20:
                print("--speakers must be 1-19", file=sys.stderr); sys.exit(1)
        title = args[args.index("--title") + 1] if "--title" in args and args.index("--title") + 1 < len(args) else ""
        ml = "--multilingual" in args
        cmd_ingest(args[1], backend, title=title, diarize=dia, speakers=spk, multilingual=ml)
    elif args[0] == "sweep":
        dry = "--dry-run" in args
        for p in store.sweep(STORE, dry_run=dry): print(f"{'would delete' if dry else 'deleted'} {p}")
        if not dry:
            from iris import library as _L
            n = _L.purge_trash(STORE)
            if n: print(f"purged {n} note(s) from Trash older than {_L.TRASH_DAYS} days")
    elif args[0] == "list":
        from iris import store as _S
        for mid in _S.list_meetings(STORE, reverse=True):
            try:
                m = json.load(open(os.path.join(STORE, mid, "meta.json")))
            except (OSError, json.JSONDecodeError):
                print(f"{mid}  (unreadable meta.json)"); continue
            title = m.get("title", "")
            enc = " [encrypted]" if m.get("encrypted") else ""
            i = m.get("integrity") or {}
            iv = f" ({i.get('passed')}/{i.get('checked')} verified)" if i else ""
            # untitled meetings store their id as the title; print it once
            print(f"{mid}{('  ' + title) if title and title != mid else ''}{enc}{iv}")

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (FileNotFoundError, RuntimeError, C.CryptoError) as e:
        print(f"error: {e}", file=sys.stderr); sys.exit(1)
