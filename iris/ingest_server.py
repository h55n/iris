"""Laptop-side ingest endpoint. The phone posts a recording over the LAN to
the user's OWN laptop (never a third-party relay); the laptop runs the full
pipeline (transcribe -> notes -> verify -> encrypt) and the result syncs
back to the phone through the normal relay as ciphertext.

  python3 iris/ingest_server.py --token S3CRET --port 8472

POST /ingest  (body = raw audio bytes, X-Convo-Token, optional X-Iris-Title)
  -> {"meeting": "<id>", "integrity": {...}}
Audio lands in store/<mid>/audio.* and is swept by the 7-day retention like
any other recording.
"""
import io, os, json, argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

def make_handler(store_dir, token, backend):
    from iris import transcribe as T, backends as B, verify, store, crypto as C, render
    class H(BaseHTTPRequestHandler):
        def _auth(self):
            return self.headers.get("X-Convo-Token") == token
        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_POST(self):
            if not self._auth(): return self._send(403, {"error": "bad token"})
            if self.path != "/ingest": return self._send(404, {})
            audio = self.rfile.read(int(self.headers["Content-Length"]))
            if len(audio) < 1000: return self._send(400, {"error": "audio too small"})
            title = self.headers.get("X-Iris-Title", self.headers.get("X-Convo-Title", ""))
            mid = store.new_meeting(store_dir, title)
            tmp = os.path.join(store_dir, mid, "audio.wav")
            with open(tmp, "wb") as f: f.write(audio)
            meta = json.load(open(os.path.join(store_dir, mid, "meta.json")))
            meta["audio_files"] = ["audio.wav"]; meta["source"] = "phone-lan"
            json.dump(meta, open(os.path.join(store_dir, mid, "meta.json"), "w"), indent=2)
            segs = T.transcribe(tmp)
            tmd = T.transcript_markdown(segs)
            store.write_text(store_dir, mid, "transcript.md", tmd)
            notes = verify.verify_notes(B.get_backend(backend).notes(tmd), segs)
            store.write_text(store_dir, mid, "notes.md", render.render_notes(mid, notes, segs))
            if os.path.exists(C.DEFAULT_KEY):
                store.encrypt_meeting(store_dir, mid)
            self._send(200, {"meeting": mid, "integrity": notes.get("integrity")})
        def log_message(self, *a): pass
    return H

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=os.environ.get("IRIS_STORE", "store"))
    ap.add_argument("--token", required=True)
    ap.add_argument("--backend", default=os.environ.get("IRIS_BACKEND", "ollama"))
    ap.add_argument("--port", type=int, default=8472)
    a = ap.parse_args()
    print(f"ingest server on :{a.port} (store {a.store})")
    HTTPServer(("0.0.0.0", a.port), make_handler(a.store, a.token, a.backend)).serve_forever()
