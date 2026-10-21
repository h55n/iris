"""Local web UI for browsing meetings. Binds 127.0.0.1 only - it serves
DECRYPTED transcripts and notes, so it must never be reachable off the
machine. No JS frameworks, no CDN, no analytics: one stdlib file.

  python3 convo/webui.py --port 8473
"""
import argparse, html, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler, HTTPServer
from convo import store as S, crypto as C

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>convo</title><style>
body{font:16px/1.5 -apple-system,system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}
a{color:#3b5bdb;text-decoration:none} .m{padding:.6rem 0;border-bottom:1px solid #eee}
.meta{color:#888;font-size:.8rem} blockquote{margin:.2rem 0 .8rem;padding-left:.8rem;border-left:3px solid #ddd;color:#555}
.badge{font-size:.7rem;background:#e7f5ff;color:#1971c2;border-radius:4px;padding:.1rem .4rem}
pre{white-space:pre-wrap;font:13px/1.4 ui-monospace,monospace;background:#f8f9fa;padding:1rem;border-radius:6px}
</style>"""

def esc(t): return html.escape(t or "")

def render_notes_md(md: str) -> str:
    out = []
    for line in md.splitlines():
        e = esc(line)
        if line.startswith("# "): out.append(f"<h1>{e[2:]}</h1>")
        elif line.startswith("## "): out.append(f"<h2>{e[3:]}</h2>")
        elif line.startswith("### "): out.append(f"<h3>{e[4:]}</h3>")
        elif line.startswith("  > "): out.append(f"<blockquote>{e[5:]}</blockquote>")
        elif line.startswith("- [ ] "): out.append(f"<div>&#9744; {e[6:]}</div>")
        elif line.startswith("- "): out.append(f"<div>&bull; {e[2:]}</div>")
        elif line.startswith("_integrity"): out.append(f'<p class=meta>{e}</p>')
        elif line.strip(): out.append(f"<p>{e}</p>")
    return "\n".join(out)

def make_handler(store_dir):
    class H(BaseHTTPRequestHandler):
        def _html(self, body):
            data = (PAGE + body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                import urllib.parse as U
                q = U.parse_qs(U.urlparse(self.path).query).get("q", [""])[0].strip()
                if q:
                    hits = S.search(store_dir, q)
                    rows = [f'<div class=m><a href="/meeting/{h["meeting"]}">{esc(h["meeting"])}</a>'
                            f'<div class=meta>{esc(h["file"])}: {esc(h["line"][:120])}</div></div>' for h in hits]
                    body = (f'<p><a href="/">&larr;</a> {len(hits)} result(s) for <b>{esc(q)}</b></p>'
                            + ("".join(rows) or "<p>nothing found</p>"))
                    return self._html(body)
                rows = []
                for mid in sorted(os.listdir(store_dir), reverse=True):
                    mp = os.path.join(store_dir, mid, "meta.json")
                    if not os.path.isfile(mp): continue
                    meta = json.load(open(mp))
                    badge = ' <span class=badge>encrypted</span>' if meta.get("encrypted") else ""
                    integ = meta.get("integrity") or {}
                    ip = f' &middot; {integ.get("passed")}/{integ.get("checked")} verified' if integ else ""
                    rows.append(f'<div class=m><a href="/meeting/{mid}">{esc(meta.get("title", mid))}</a>{badge}'
                                f'<div class=meta>{mid}{ip}</div></div>')
                form = ('<form method=get><input name=q placeholder="search all meetings" '
                        'style="width:70%;padding:.4rem"> <button>search</button></form>')
                self._html(f"<h1>convo</h1>{form}{''.join(rows) or '<p>No meetings yet.</p>'}")
            elif self.path.startswith("/meeting/"):
                mid = self.path.split("/meeting/", 1)[1].strip("/")
                if "/" in mid or ".." in mid or not os.path.isdir(os.path.join(store_dir, mid)):
                    self._html("<p>not found</p>"); return
                texts = (S.decrypt_meeting(store_dir, mid) if S.is_encrypted(store_dir, mid)
                         else {n: open(os.path.join(store_dir, mid, n)).read()
                               for n in S.PLAINTEXT_FILES if os.path.exists(os.path.join(store_dir, mid, n))})
                body = '<p><a href="/">&larr; all meetings</a></p>'
                if "notes.md" in texts: body += render_notes_md(texts["notes.md"])
                if "transcript.md" in texts: body += f"<h2>Transcript</h2><pre>{esc(texts['transcript.md'])}</pre>"
                self._html(body)
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a): pass
    return H

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=os.environ.get("CONVO_STORE", "store"))
    ap.add_argument("--port", type=int, default=8473)
    a = ap.parse_args()
    print(f"convo UI on http://127.0.0.1:{a.port} (local only - serves decrypted content)")
    HTTPServer(("127.0.0.1", a.port), make_handler(a.store)).serve_forever()
