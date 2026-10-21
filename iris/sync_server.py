"""Tiny self-hostable sync server. Moves transcripts, notes and meta between
your devices. NEVER audio - recordings never leave the device they were made on.
stdlib only: python3 iris/sync_server.py --dir syncdata --token S3CRET --port 8471"""
import json, os, time, argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

def make_handler(root, token):
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
            if not self.path.startswith("/push/"): return self._send(404, {})
            mid = self.path.split("/push/", 1)[1].strip("/")
            if "/" in mid or ".." in mid: return self._send(400, {"error": "bad id"})
            bundle = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if "audio" in bundle or "audio_b64" in bundle:
                return self._send(400, {"error": "audio never syncs"})
            d = os.path.join(root, mid)
            os.makedirs(d, exist_ok=True)
            bundle["_server_ts"] = time.time()
            with open(os.path.join(d, "bundle.json"), "w") as f:
                json.dump(bundle, f)
            self._send(200, {"ok": True, "id": mid})
        def do_GET(self):
            if not self._auth(): return self._send(403, {"error": "bad token"})
            if self.path.startswith("/list"):
                since = 0.0
                if "since=" in self.path:
                    since = float(self.path.split("since=")[1].split("&")[0])
                out = []
                for mid in sorted(os.listdir(root)):
                    p = os.path.join(root, mid, "bundle.json")
                    if os.path.isfile(p):
                        b = json.load(open(p))
                        if b.get("_server_ts", 0) > since:
                            out.append({"id": mid, "ts": b["_server_ts"]})
                return self._send(200, {"meetings": out})
            if self.path.startswith("/pull/"):
                mid = self.path.split("/pull/", 1)[1].strip("/")
                p = os.path.join(root, mid, "bundle.json")
                if not os.path.isfile(p): return self._send(404, {})
                return self._send(200, json.load(open(p)))
            self._send(404, {})
        def log_message(self, *a): pass
    return H

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="syncdata")
    ap.add_argument("--token", required=True)
    ap.add_argument("--port", type=int, default=8471)
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    print(f"sync server on :{a.port}, data in {a.dir}")
    HTTPServer(("0.0.0.0", a.port), make_handler(a.dir, a.token)).serve_forever()
