"""Audio bytes in, verified notes out. Shared by the phone ingest server and
the web app's in-browser recorder so both take the same path."""
import json, os

class PipelineError(Exception):
    def __init__(self, message, meeting):
        super().__init__(message); self.meeting = meeting

def process_audio(store_dir: str, audio: bytes, title: str = "", backend: str = "ollama",
                  source: str = "phone-lan", ext: str = "wav") -> dict:
    """Stores the audio, transcribes, writes verified notes, encrypts if a key exists.
    Raises PipelineError (audio kept on disk) if a later step fails."""
    from iris import transcribe as T, backends as B, verify, store, crypto as C, render
    ext = "".join(ch for ch in ext.lower() if ch.isalnum())[:5] or "wav"
    mid = store.new_meeting(store_dir, title)
    name = f"audio.{ext}"
    tmp = os.path.join(store_dir, mid, name)
    with open(tmp, "wb") as f: f.write(audio)
    mp = os.path.join(store_dir, mid, "meta.json")
    meta = json.load(open(mp))
    meta["audio_files"] = [name]; meta["source"] = source
    json.dump(meta, open(mp, "w"), indent=2)
    try:
        segs = T.transcribe(tmp)
        tmd = T.transcript_markdown(segs)
        store.write_text(store_dir, mid, "transcript.md", tmd)
        notes = verify.verify_notes(B.get_backend(backend).notes(tmd), segs)
        store.write_text(store_dir, mid, "notes.md", render.render_notes(mid, notes, segs))
        if os.path.exists(C.DEFAULT_KEY):
            store.encrypt_meeting(store_dir, mid)
    except Exception as e:
        raise PipelineError(f"{type(e).__name__}: {e}", mid) from e
    return {"meeting": mid, "integrity": notes.get("integrity")}
