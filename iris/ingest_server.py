"""Laptop-side ingest endpoint. The phone posts a recording over the LAN to
the user's OWN laptop (never a third-party relay); the laptop runs the full
pipeline (transcribe -> notes -> verify -> encrypt) and the result syncs
back to the phone through the normal relay as ciphertext.

  python3 iris/ingest_server.py --token S3CRET --port 8472

POST /ingest  (body = raw audio bytes, X-Iris-Token, optional X-Iris-Title,
               optional X-Iris-Language: en|hi|ta|... (2-3 letter code),
               optional X-Iris-Multilingual: 1 (mixed Hinglish: per-segment detect),
               optional X-Iris-Careful: 1 (measured-accuracy decode, slower),
               optional X-Iris-Allow-Unsupported: 1 (force e.g. bn past the guard))
  -> {"meeting": "<id>", "integrity": {...}}
Audio lands in store/<mid>/audio.* and is swept by the 7-day retention like
any other recording.
"""
import io, os, json, argparse, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _meeting_title(headers) -> str:
    """New header wins; legacy X-Convo-Title keeps already-built APKs working."""
    return headers.get("X-Iris-Title", headers.get("X-Convo-Title", ""))

def _on(headers, name) -> bool:
    return headers.get(name, "").strip().lower() in ("1", "true", "yes", "on")

def _transcription_opts(headers):
    """Phone-declared transcription settings -> (opts, error). Defaults keep the
    pre-header behavior exactly: English, single language, standard decode."""
    import re
    from iris import transcribe as T
    lang = headers.get("X-Iris-Language", "en").strip().lower() or "en"
    if not re.fullmatch(r"[a-z]{2,3}", lang):
        return None, f"bad X-Iris-Language: {lang!r} (e.g. en, hi, ta)"
    multilingual = _on(headers, "X-Iris-Multilingual")
    if multilingual and lang != "en":
        return None, "X-Iris-Language and X-Iris-Multilingual conflict (multilingual auto-detects)"
    allow = _on(headers, "X-Iris-Allow-Unsupported")
    if lang in T.UNSUPPORTED_LANGS and not allow:
        return None, (f"{lang} is not supported (whisper writes the wrong script, measured "
                      f"100% WER) - send X-Iris-Allow-Unsupported: 1 to force it anyway")
    return {"language": lang, "multilingual": multilingual,
            "careful": _on(headers, "X-Iris-Careful"), "allow_unsupported": allow}, None

def make_handler(store_dir, token, backend):
    from iris import transcribe as T, backends as B, verify, store, crypto as C, render  # noqa: F401 (T used by do_POST)
    class H(BaseHTTPRequestHandler):
        def _auth(self):
            import hmac
            return hmac.compare_digest(self.headers.get("X-Iris-Token", self.headers.get("X-Convo-Token")) or "", token)
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
            try:
                size = int(self.headers["Content-Length"])
            except (TypeError, ValueError):
                return self._send(400, {"error": "bad Content-Length"})
            if size > 500 * 1024 * 1024:  # 500 MB sanity cap (~9h of 16k mono wav)
                return self._send(413, {"error": "audio too large"})
            audio = self.rfile.read(size)
            if len(audio) < 1000: return self._send(400, {"error": "audio too small"})
            opts, err = _transcription_opts(self.headers)
            if err: return self._send(400, {"error": err})
            from iris.pipeline import process_audio, PipelineError
            try:
                out = process_audio(store_dir, audio, _meeting_title(self.headers), backend, **opts)
            except T.UnsupportedLanguageError as e:
                return self._send(400, {"error": str(e)})
            except PipelineError as e:
                # audio is kept on disk; the phone gets a real answer, not a dropped socket
                return self._send(500, {"error": str(e), "meeting": e.meeting})
            self._send(200, out)
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
