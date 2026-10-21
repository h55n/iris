#!/usr/bin/env python3
"""Iris - private meeting notes. ingest | sweep | list | sync | key | encrypt | read | export | share | search | enroll | voices | doctor"""
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
            print("diarize models missing - run models/get-diarize-models.sh")
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

__version__ = "0.2.0"

if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--version"]:
        print(f"iris {__version__}"); sys.exit(0)
    if not args or args[0] not in ("ingest", "sweep", "list", "sync", "key", "encrypt", "read", "export", "share", "search", "enroll", "voices", "doctor"):
        print(__doc__); sys.exit(1)
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
            print("public key:", C.generate_key())
        elif len(args) > 1 and args[1] == "export":
            print(C.export_secret())
        elif len(args) > 1 and args[1] == "qr":
            print(C.export_qr())
        elif len(args) > 1 and args[1] == "info":
            print(C.key_info())
        else:
            print(C.public_key())
    elif args[0] == "encrypt":
        mids = [args[1]] if len(args) > 1 else [m for m in sorted(os.listdir(STORE)) if os.path.isdir(os.path.join(STORE, m))]
        for m in mids:
            if not store.is_encrypted(STORE, m):
                print(m, "->", ", ".join(store.encrypt_meeting(STORE, m)))
    elif args[0] == "search":
        for h in store.search(STORE, " ".join(args[1:])):
            print(f"{h['meeting']} ({h['file']}): {h['line']}")
    elif args[0] == "export":
        from iris import export as E
        print(E.export_meeting(STORE, args[1], args[2]))
    elif args[0] == "share":
        from iris import export as E
        print(E.share_meeting(STORE, args[1], args[2], args[3]))
    elif args[0] == "read":
        if len(args) < 2 or not os.path.isdir(os.path.join(STORE, args[1])):
            print(f"no such meeting: {args[1] if len(args) > 1 else '(missing id)'}", file=sys.stderr)
            print("try: iris list", file=sys.stderr)
            sys.exit(1)
        for name, text in store.decrypt_meeting(STORE, args[1]).items():
            print(f"--- {name} ---\n{text}")
    elif args[0] == "sync":
        import getpass
        server = args[args.index("--server") + 1] if "--server" in args else os.environ.get("IRIS_SYNC_SERVER", "http://127.0.0.1:8471")
        token = os.environ.get("IRIS_SYNC_TOKEN") or getpass.getpass("sync token: ")
        from iris import sync as S
        pushed, skipped = S.push_changed(STORE, server, token)
        st = S.state_file(STORE)
        got = S.pull_all(STORE, server, token, st.get("last_pull", 0.0))
        st["last_pull"] = __import__("time").time(); S.save_state(STORE, st)
        print(f"pushed {len(pushed)} ({len(skipped)} unchanged), pulled {len(got)}: {got}")
    elif args[0] == "ingest":
        if len(args) < 2 or not os.path.exists(args[1]):
            print("usage: iris ingest <audio-file> [--backend ollama|ultramarine] [--diarize [--speakers N]] [--multilingual] [--title T]"); sys.exit(1)
        backend = "ollama"
        if "--backend" in args:
            i = args.index("--backend"); backend = args[i + 1]; del args[i:i + 2]
        dia = "--diarize" in args
        spk = int(args[args.index("--speakers") + 1]) if "--speakers" in args else 0
        title = args[args.index("--title") + 1] if "--title" in args else ""
        ml = "--multilingual" in args
        cmd_ingest(args[1], backend, title=title, diarize=dia, speakers=spk, multilingual=ml)
    elif args[0] == "sweep":
        dry = "--dry-run" in args
        for p in store.sweep(STORE, dry_run=dry): print(f"{'would delete' if dry else 'deleted'} {p}")
    elif args[0] == "list":
        from iris import store as _S
        for mid in _S.list_meetings(STORE, reverse=True):
            m = json.load(open(os.path.join(STORE, mid, "meta.json")))
            title = m.get("title", "")
            enc = " [encrypted]" if m.get("encrypted") else ""
            i = m.get("integrity") or {}
            iv = f" ({i.get('passed')}/{i.get('checked')} verified)" if i else ""
            # untitled meetings store their id as the title; print it once
            print(f"{mid}{('  ' + title) if title and title != mid else ''}{enc}{iv}")
