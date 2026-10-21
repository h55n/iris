"""Local web UI for browsing meetings. Binds 127.0.0.1 only - it serves
DECRYPTED transcripts and notes, so it must never be reachable off the
machine. Design: Notion/Granola/macOS - calm document reading, soft neutrals.

  python3 convo/webui.py --port 8473
"""
import argparse, html, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iris import store as S

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>convo</title><style>
:root{
  --bg:#ffffff; --side:#f7f7f5; --text:#37352f; --muted:#73726e; --faint:#a3a29e;
  --border:#e9e9e7; --border-soft:#ededeb; --accent:#2383e2;
  --quote-border:#d3d1cb; --pill-ok-bg:#eef7ee; --pill-ok:#2f6b31;
}
*{box-sizing:border-box}
body{margin:0;font:16px/1.65 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,sans-serif;
  color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased}
.layout{display:flex;min-height:100vh}
.sidebar{width:264px;flex:none;background:var(--side);border-right:1px solid var(--border-soft);
  padding:18px 12px;position:sticky;top:0;height:100vh;overflow:auto}
.brand{font-weight:600;font-size:15px;padding:4px 10px 14px;letter-spacing:.1px}
.brand span{color:var(--faint);font-weight:400;font-size:12px;display:block;margin-top:2px}
.searchbox{margin:0 6px 12px}
.searchbox input{width:100%;padding:6px 10px;font-size:13px;border:1px solid var(--border);
  border-radius:6px;background:#fff;color:var(--text);outline:none}
.searchbox input:focus{border-color:var(--accent)}
.nav-item{display:block;padding:6px 10px;border-radius:6px;color:var(--text);text-decoration:none;margin-bottom:1px}
.nav-item:hover{background:#ececea}
.nav-item.active{background:#e3e3e0}
.nav-title{font-size:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nav-meta{font-size:11.5px;color:var(--faint);margin-top:1px}
.content{flex:1;min-width:0}
.doc{max-width:760px;margin:0 auto;padding:56px 72px 120px}
h1{font-size:30px;font-weight:700;line-height:1.25;margin:0 0 6px;letter-spacing:-.01em}
.doc-meta{color:var(--muted);font-size:13px;margin-bottom:36px}
h2{font-size:20px;font-weight:600;margin:36px 0 10px;letter-spacing:-.005em}
h3{font-size:16px;font-weight:600;margin:24px 0 8px}
p{margin:6px 0}
.todo{display:flex;gap:8px;align-items:flex-start;margin:6px 0}
.todo .box{flex:none;width:15px;height:15px;border:1.5px solid var(--faint);border-radius:3px;margin-top:5px}
.bullet{margin:6px 0;padding-left:22px;position:relative}
.bullet:before{content:"";position:absolute;left:6px;top:.72em;width:5px;height:5px;border-radius:50%;background:var(--text)}
blockquote{margin:2px 0 14px;padding:2px 0 2px 14px;border-left:3px solid var(--quote-border);
  color:#6f6e69;font-size:14.5px}
blockquote .ts{color:var(--faint);font-size:12.5px}
.pill{display:inline-block;font-size:12px;padding:2px 10px;border-radius:999px;
  background:var(--pill-ok-bg);color:var(--pill-ok);font-weight:500}
.speaker{display:inline-block;font-size:11.5px;font-weight:600;padding:1px 8px;border-radius:999px;
  margin-right:6px;vertical-align:1px}
pre.transcript{background:var(--side);border:1px solid var(--border-soft);border-radius:8px;
  padding:18px 20px;font:13px/1.8 ui-monospace,"SF Mono",Menlo,monospace;white-space:pre-wrap;color:#4a4844}
.back{color:var(--muted);text-decoration:none;font-size:13.5px}
.back:hover{color:var(--text)}
.divider{border:none;border-top:1px solid var(--border-soft);margin:40px 0}
@media (max-width:900px){
  .layout{flex-direction:column}
  .sidebar{width:100%;height:auto;position:static;border-right:none;border-bottom:1px solid var(--border-soft)}
  .doc{padding:32px 22px 80px}
  h1{font-size:25px}
}
</style>"""

def esc(t): return html.escape(t or "")

SPEAKER_COLORS = [
    ("#e8f0fe", "#1a56c4"), ("#fdeeee", "#b83232"), ("#e9f6ec", "#2f6b31"),
    ("#fdf3e3", "#96610f"), ("#f3ecfa", "#6b3fa0"), ("#e8f5f4", "#0f6e63"),
]

def speaker_chip(n: int) -> str:
    bg, fg = SPEAKER_COLORS[n % len(SPEAKER_COLORS)]
    return f'<span class=speaker style="background:{bg};color:{fg}">Speaker {n + 1}</span>'

def render_transcript_line(line: str) -> str:
    """[mm:ss] Speaker N: text  ->  timestamp + chip + text"""
    import re
    m = re.match(r"^\[(\d\d:\d\d)\] (?:Speaker (\d+): )?(.*)$", line)
    if not m:
        return esc(line)
    ts, spk, text = m.group(1), m.group(2), m.group(3)
    chip = speaker_chip(int(spk) - 1) if spk else ""
    return f'<span style="color:var(--faint)">{ts}</span>  {chip}{esc(text)}'

def render_notes_md(md: str) -> str:
    out = []
    for line in md.splitlines():
        if line.startswith("# "):
            continue  # page title already shown
        if line.startswith("## "):
            out.append(f"<h2>{esc(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{esc(line[4:])}</h3>")
        elif line.startswith("  > "):
            body = line[4:]
            import re
            m = re.match(r'^"(.*)"\s*\[(\d\d:\d\d)\]$', body)
            if m:
                out.append(f'<blockquote>&ldquo;{esc(m.group(1))}&rdquo; <span class=ts>{m.group(2)}</span></blockquote>')
            else:
                out.append(f"<blockquote>{esc(body)}</blockquote>")
        elif line.startswith("- [ ] "):
            out.append(f'<div class=todo><span class=box></span><span>{esc(line[6:])}</span></div>')
        elif line.startswith("- "):
            out.append(f'<div class=bullet>{esc(line[2:])}</div>')
        elif line.startswith("_integrity"):
            import re
            m = re.search(r"(\d+)/(\d+)", line)
            label = f"{m.group(1)}/{m.group(2)} claims verified" if m else esc(line)
            out.append(f'<p><span class=pill>{label}</span></p>')
        elif line.strip():
            out.append(f"<p>{esc(line)}</p>")
    return "\n".join(out)

def sidebar(store_dir: str, active: str | None) -> str:
    items = []
    for mid in sorted(os.listdir(store_dir), reverse=True):
        mp = os.path.join(store_dir, mid, "meta.json")
        if not os.path.isfile(mp):
            continue
        meta = json.load(open(mp))
        integ = meta.get("integrity") or {}
        iv = f' &middot; {integ.get("passed")}/{integ.get("checked")} verified' if integ else ""
        when = time.strftime("%b %-d, %-I:%M %p", time.localtime(meta.get("created", 0)))
        cls = "nav-item active" if mid == active else "nav-item"
        items.append(f'<a class="{cls}" href="/meeting/{mid}">'
                     f'<div class=nav-title>{esc(meta.get("title", mid))}</div>'
                     f'<div class=nav-meta>{when}{iv}</div></a>')
    return ('<div class=brand>convo<span>private meeting notes</span></div>'
            '<form class=searchbox method=get action="/search">'
            '<input name=q placeholder="Search meetings"></form>'
            + ("".join(items) or '<div class=nav-meta style="padding:0 10px">No meetings yet.</div>'))

def page(inner: str) -> bytes:
    return (PAGE + inner).encode()

def make_handler(store_dir: str):
    class H(BaseHTTPRequestHandler := __import__("http.server", fromlist=["BaseHTTPRequestHandler"]).BaseHTTPRequestHandler):
        def _html(self, body: str):
            data = page(f'<div class=layout><nav class=sidebar>{sidebar(store_dir, self._active)}</nav>'
                        f'<main class=content><div class=doc>{body}</div></main></div>')
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        _active = None
        def do_GET(self):
            import urllib.parse as U
            path = U.urlparse(self.path).path
            if path == "/":
                self._active = None
                self._html('<h1 style="margin-top:24px">Meetings</h1>'
                           '<p class=doc-meta>Pick a meeting on the left, or search above.</p>')
            elif path == "/search":
                q = U.parse_qs(U.urlparse(self.path).query).get("q", [""])[0].strip()
                self._active = None
                if not q:
                    return self._html("<h1>Search</h1><p class=doc-meta>Type something in the search box.</p>")
                hits = S.search(store_dir, q)
                rows = "".join(
                    f'<div style="margin-bottom:14px"><a class=nav-title href="/meeting/{h["meeting"]}">{esc(h["meeting"])}</a>'
                    f'<div class=nav-meta>{esc(h["file"])}</div><p style="margin-top:2px">{esc(h["line"][:200])}</p></div>'
                    for h in hits)
                self._html(f'<h1>Search</h1><p class=doc-meta>{len(hits)} result(s) for &ldquo;{esc(q)}&rdquo;</p>'
                           + (rows or "<p>Nothing found.</p>"))
            elif path.startswith("/meeting/"):
                mid = path.split("/meeting/", 1)[1].strip("/")
                self._active = mid
                if "/" in mid or ".." in mid or not os.path.isdir(os.path.join(store_dir, mid)):
                    self._html("<p>not found</p>"); return
                meta = json.load(open(os.path.join(store_dir, mid, "meta.json")))
                texts = (S.decrypt_meeting(store_dir, mid) if S.is_encrypted(store_dir, mid)
                         else {n: open(os.path.join(store_dir, mid, n)).read()
                               for n in S.PLAINTEXT_FILES if os.path.exists(os.path.join(store_dir, mid, n))})
                when = time.strftime("%B %-d, %Y at %-I:%M %p", time.localtime(meta.get("created", 0)))
                body = (f'<h1>{esc(meta.get("title", mid))}</h1><div class=doc-meta>{when} &middot; {mid}</div>')
                if "notes.md" in texts:
                    body += render_notes_md(texts["notes.md"])
                if "transcript.md" in texts:
                    lines = "<br>".join(render_transcript_line(l) for l in texts["transcript.md"].splitlines())
                    body += f'<hr class=divider><h2>Transcript</h2><pre class=transcript>{lines}</pre>'
                self._html(body)
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a): pass
    return H

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=os.environ.get("IRIS_STORE", "store"))
    ap.add_argument("--port", type=int, default=8473)
    a = ap.parse_args()
    from http.server import HTTPServer
    print(f"convo UI on http://127.0.0.1:{a.port} (local only - serves decrypted content)")
    HTTPServer(("127.0.0.1", a.port), make_handler(a.store)).serve_forever()
