"""Local web UI for browsing meetings. Binds 127.0.0.1 only - it serves
DECRYPTED transcripts and notes, so it must never be reachable off the
machine. Design: Notion/Granola/macOS - calm document reading, soft neutrals.

  python3 iris/webui.py --port 8473
"""
import argparse, html, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iris import store as S

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Iris</title>
<script>try{var t=localStorage.getItem("iris-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}</script>
<style>
:root{
  --bg:#fdfdfc; --side:#f7f7f2; --text:#37352f; --muted:#73726e; --faint:#a3a29e;
  --border:#e9e9e7; --border-soft:#ededeb; --accent:#2383e2;
  --quote-border:#d3d1cb; --pill-ok-bg:#eef7ee; --pill-ok:#2f6b31;
  --input-bg:#ffffff; --active-bg:#e3e3e0; --danger:#b83232; --danger-border:#e5c7c5;
  --accent-soft:#e7f0fb;
}
[data-theme=green]{ --accent:#0f7b6c; --accent-soft:#e2f1ee; }
[data-theme=purple]{ --accent:#6940a5; --accent-soft:#efeaf7; }
[data-theme=orange]{ --accent:#d9730d; --accent-soft:#faebdd; }
[data-theme=pink]{ --accent:#c14c8a; --accent-soft:#f8e9f1; }
[data-theme=red]{ --accent:#d44c47; --accent-soft:#fae9e8; }
@media (prefers-color-scheme: dark){
  :root{
    --bg:#191919; --side:#202020; --text:#d4d4d2; --muted:#9b9b98; --faint:#6f6f6c;
    --border:#2f2f2f; --border-soft:#2a2a2a; --accent:#529cca;
    --quote-border:#4a4a47; --pill-ok-bg:#1e2b1e; --pill-ok:#6aaa6f;
    --input-bg:#252525; --active-bg:#373737; --danger:#e08a8a; --danger-border:#5a3535;
    --accent-soft:#1c2f3d;
  }
  [data-theme=green]{ --accent:#4dab9a; --accent-soft:#1d2f2b; }
  [data-theme=purple]{ --accent:#a98fd4; --accent-soft:#2a2436; }
  [data-theme=orange]{ --accent:#e8a35c; --accent-soft:#332a1e; }
  [data-theme=pink]{ --accent:#e08ab5; --accent-soft:#33222b; }
  [data-theme=red]{ --accent:#e88a86; --accent-soft:#332020; }
}
.themes{flex:none;display:flex;gap:9px;padding:10px 10px 6px;align-items:center;
  margin-top:12px;border-top:1px solid var(--border-soft)}
.themes .lbl{font-size:11px;color:var(--faint);flex:1}
.dot{width:14px;height:14px}
.dot{width:16px;height:16px;border-radius:50%;border:2px solid transparent;cursor:pointer;padding:0}
.dot.sel{border-color:var(--text)}
.dot[data-t=""]{background:#2383e2}.dot[data-t=green]{background:#0f7b6c}
.dot[data-t=purple]{background:#6940a5}.dot[data-t=orange]{background:#d9730d}
.dot[data-t=pink]{background:#c14c8a}.dot[data-t=red]{background:#d44c47}
*{box-sizing:border-box}
:root{--spring:cubic-bezier(.22,1,.36,1);--snap:cubic-bezier(.34,1.4,.44,1)}
body{animation:pagein .45s var(--spring)}
@keyframes pagein{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.nav-item{transition:background .25s var(--spring),transform .25s var(--spring)}
.nav-item:hover{transform:translateX(2px)}
a{transition:color .2s var(--spring)}
button{transition:transform .18s var(--snap),border-color .25s var(--spring),background .25s var(--spring);cursor:pointer}
button:hover{transform:translateY(-1px)}
button:active{transform:scale(.94)}
.dot{transition:transform .25s var(--snap)}
.dot:hover{transform:scale(1.25)}
input{transition:border-color .25s var(--spring),box-shadow .25s var(--spring)}
input:focus{box-shadow:0 0 0 3px var(--accent-soft)}
.bullet,.todo,blockquote,.nav-item,h2,h3,.pill{animation:rise .5s var(--spring) both}
.rise:nth-child(2){animation-delay:.04s}.rise:nth-child(3){animation-delay:.08s}
.rise:nth-child(4){animation-delay:.12s}.rise:nth-child(5){animation-delay:.16s}
.rise:nth-child(6){animation-delay:.2s}.rise:nth-child(7){animation-delay:.24s}
.rise:nth-child(n+8){animation-delay:.28s}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
body{margin:0;font:16px/1.65 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,sans-serif;
  color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased}
.layout{display:flex;min-height:100vh}
.sidebar{width:264px;flex:none;background:var(--side);border-right:1px solid var(--border-soft);
  padding:18px 12px 10px;position:sticky;top:0;height:100vh;overflow:auto;
  display:flex;flex-direction:column}
.nav{flex:1 1 auto;min-height:0}
.brand{font-weight:600;font-size:15px;padding:4px 10px 14px;letter-spacing:.1px}
.brand span{color:var(--faint);font-weight:400;font-size:12px;display:block;margin-top:2px}
.searchbox{margin:0 6px 12px}
.searchbox input{width:100%;padding:6px 10px;font-size:13px;border:1px solid var(--border);
  border-radius:6px;background:var(--input-bg);color:var(--text);outline:none}
.searchbox input:focus{border-color:var(--accent)}
.nav-item{display:block;padding:6px 10px;border-radius:6px;color:var(--text);text-decoration:none;margin-bottom:1px}
.nav-item:hover{background:#ececea}
.nav-item.active{background:var(--active-bg)}
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
  margin-right:6px;vertical-align:1px;animation:rise .4s var(--spring) both}
.spk0{background:#e8f0fe;color:#1a56c4}.spk1{background:#fdeeee;color:#b83232}
.spk2{background:#e9f6ec;color:#2f6b31}.spk3{background:#fdf3e3;color:#96610f}
.spk4{background:#f3ecfa;color:#6b3fa0}.spk5{background:#e8f5f4;color:#0f6e63}
@media (prefers-color-scheme: dark){
  .spk0{background:#1e2c45;color:#7fa8ec}.spk1{background:#3a2020;color:#ec8a8a}
  .spk2{background:#1d3020;color:#86c98c}.spk3{background:#332812;color:#e0b36a}
  .spk4{background:#2b2138;color:#c0a3e8}.spk5{background:#16302d;color:#6ec9bf}
}
h2 .icon, h3 .icon{width:18px;height:18px;vertical-align:-3px;margin-right:7px;color:var(--accent)}
.mascot{display:block;margin:26px auto 10px;cursor:pointer;
  animation:floaty 3.6s ease-in-out infinite;transform-origin:center 70%}
@keyframes floaty{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
.mascot.wink{animation:wink .5s var(--snap)}
@keyframes wink{30%{transform:scaleY(.82) translateY(4px)}60%{transform:scaleY(1.06)}}
.empty{text-align:center;color:var(--muted);padding:28px 12px 8px}
.empty .t{font-size:15px;color:var(--text);font-weight:500;margin-top:6px}
.empty .s{font-size:13px;margin-top:2px}
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

# Iris the eye - original SVG mascot drawn for this project (no third-party art)
def mascot(size: int = 96, mood: str = "happy") -> str:
    smile = ('<path d="M47 83 q13 11 26 0" stroke="currentColor" stroke-width="3.2" '
             'fill="none" stroke-linecap="round"/>') if mood == "happy" else (
            '<path d="M50 85 q10 5 20 0" stroke="currentColor" stroke-width="3.2" '
            'fill="none" stroke-linecap="round" opacity=".65"/>'
            '<text x="86" y="34" font-size="15" fill="var(--faint)" font-family="sans-serif">z</text>'
            '<text x="95" y="24" font-size="11" fill="var(--faint)" font-family="sans-serif">z</text>')
    if mood == "celebrate":
        smile = ('<path d="M45 82 q15 13 30 0" stroke="currentColor" stroke-width="3.2" '
                 'fill="none" stroke-linecap="round"/>'
                 '<path d="M52 30 L60 6 L68 30 Z" fill="var(--accent)" stroke="currentColor" '
                 'stroke-width="2.6" stroke-linejoin="round"/>'
                 '<circle cx="60" cy="6" r="3.4" fill="var(--accent)"/>'
                 '<path d="M20 24 l4 4 M100 22 l-4 4 M14 44 l5 2 M106 42 l-5 2" '
                 'stroke="var(--accent)" stroke-width="3" stroke-linecap="round"/>'
                 '<circle cx="28" cy="14" r="3" fill="var(--accent)" opacity=".7"/>'
                 '<circle cx="94" cy="12" r="3" fill="var(--accent)" opacity=".7"/>')
    return (f'<svg class=mascot width="{size}" height="{size}" viewBox="0 0 120 120" '
            'fill="none" aria-hidden="true" style="color:var(--text)">'
            '<ellipse cx="60" cy="64" rx="36" ry="32" fill="var(--accent-soft)"/>'
            '<ellipse cx="60" cy="64" rx="36" ry="32" stroke="currentColor" stroke-width="3.2"/>'
            '<path d="M24 60 q-8 -4 -6 -12" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"/>'
            '<path d="M96 60 q8 -4 6 -12" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"/>'
            '<circle cx="60" cy="60" r="15.5" fill="var(--bg)" stroke="currentColor" stroke-width="3.2"/>'
            '<circle cx="62.5" cy="62.5" r="6.5" fill="var(--accent)"/>'
            '<circle cx="59.5" cy="58" r="2.2" fill="var(--bg)"/>'
            + smile +
            '<path d="M45 95 l-3 9 M75 95 l3 9" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"/>'
            '<circle cx="38" cy="76" r="3.4" fill="var(--accent)" opacity=".45"/>'
            '<circle cx="82" cy="76" r="3.4" fill="var(--accent)" opacity=".45"/>'
            '</svg>')

def confetti(mid: str) -> str:
    """One-time celebrate burst the first time a fresh (<10 min) meeting is opened."""
    return (f"<script>(function(){{try{{if(localStorage.getItem('iris-party-{mid}'))return;"
            "localStorage.setItem('iris-party-" + mid + "','1')}catch(e){{}}"
            "var C=['#2383e2','#0f7b6c','#6940a5','#d9730d','#c14c8a','#d44c47'];"
            "for(var i=0;i<42;i++){var d=document.createElement('div');"
            "d.style.cssText='position:fixed;top:-12px;left:'+(Math.random()*100)+'vw;width:'+"
            "(5+Math.random()*6)+'px;height:'+(8+Math.random()*8)+'px;background:'+C[i%6]+';"
            "border-radius:2px;z-index:99;pointer-events:none;"
            "transform:rotate('+(Math.random()*360)+'deg);"
            "transition:transform '+(1.6+Math.random()*1.4)+'s cubic-bezier(.22,1,.36,1),opacity .4s 2.4s;';"
            "document.body.appendChild(d);"
            "requestAnimationFrame(function(el){return function(){"
            "el.style.transform='translateY('+(window.innerHeight+40)+'px) rotate('+(360+Math.random()*720)+'deg)';"
            "el.style.opacity='0'}}(d));"
            "setTimeout(function(el){return function(){el.remove()}}(d),3200)}}})();</script>")

ICONS = {
    "summary": '<svg class=icon viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 5h14M5 10h14M5 15h9"/></svg>',
    "decisions": '<svg class=icon viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/></svg>',
    "action items": '<svg class=icon viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/></svg>',
    "unverified": '<svg class=icon viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.2v.3"/></svg>',
    "transcript": '<svg class=icon viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17c-2 0-3.5-1.6-3.5-3.5C3.5 9.6 6 7 9.5 6.5M17 17c-2 0-3.5-1.6-3.5-3.5 0-3.9 2.5-6.5 6-7"/></svg>',
}

def heading_icon(title: str) -> str:
    return ICONS.get(title.strip().lower(), ICONS["summary"])

N_SPEAKER_COLORS = 6

def speaker_chip(n: int, label: str | None = None) -> str:
    return f'<span class="speaker spk{n % N_SPEAKER_COLORS}">{esc(label or "Speaker " + str(n + 1))}</span>'

def render_transcript_line(line: str) -> str:
    """[mm:ss] Speaker N: text / [mm:ss] Name: text -> timestamp + chip + text"""
    import re
    m = re.match(r"^\[(\d\d:\d\d)\] (?:(Speaker \d+)|([A-Za-z][\w-]*)): (.*)$", line)
    if m:
        ts, numbered, name, text = m.groups()
        label = numbered or name
        idx = (int(numbered.split()[1]) - 1) if numbered else (sum(label.encode()) % N_SPEAKER_COLORS)
        chip = speaker_chip(idx, label)
        return f'<span style="color:var(--faint)">{ts}</span>  {chip}{esc(text)}'
    m2 = re.match(r"^\[(\d\d:\d\d)\] (.*)$", line)
    if m2:
        return f'<span style="color:var(--faint)">{m2.group(1)}</span>  {esc(m2.group(2))}'
    return esc(line)

def render_notes_md(md: str) -> str:
    out = []
    for line in md.splitlines():
        if line.startswith("# "):
            continue  # page title already shown
        if line.startswith("## "):
            t = line[3:]
            out.append(f"<h2>{heading_icon(t)}{esc(t)}</h2>")
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
    for mid in S.list_meetings(store_dir, reverse=True):
        meta = json.load(open(os.path.join(store_dir, mid, "meta.json")))
        integ = meta.get("integrity") or {}
        iv = f' &middot; {integ.get("passed")}/{integ.get("checked")} verified' if integ else ""
        when = time.strftime("%b %-d, %-I:%M %p", time.localtime(meta.get("created", 0)))
        cls = "nav-item active" if mid == active else "nav-item"
        items.append(f'<a class="{cls}" href="/meeting/{mid}">'
                     f'<div class=nav-title>{esc(meta.get("title", mid))}</div>'
                     f'<div class=nav-meta>{when}{iv}</div></a>')
    return ('<div class=brand>Iris<span id=tagline>private meeting notes</span></div>'
            '<script>(function(){var t=["private meeting notes","your meetings, your machines",'
            '"nothing leaves your devices","notes that keep receipts","always local, always yours"];'
            'var i=Math.floor(Math.random()*t.length),el=document.getElementById("tagline");'
            'if(el)el.textContent=t[i]})()</script>'
            '<form class=searchbox method=get action="/search">'
            '<input name=q placeholder="Search meetings"></form>'
            + '<div class=nav">'
            + ("".join(items) or '<div class=empty>' + mascot(72, "sleep")
               + '<div class=t>No meetings yet</div>'
               + '<div class=s>record one and Iris will keep it safe</div></div>')
            + '</div>'
            + '<div class=themes"><span class=lbl>Theme</span>'
            + ''.join(f'<button class=dot data-t="{t}" title="{t or "blue"}" '
                      f'onclick="pickTheme(\'{t}\',this)"></button>'
                      for t in ("", "green", "purple", "orange", "pink", "red"))
            + '</div>'
            + '<script>document.addEventListener("click",function(e){'
              'var m=e.target.closest&&e.target.closest(".mascot");'
              'if(m){m.classList.remove("wink");void m.offsetWidth;m.classList.add("wink")}});'
              'function pickTheme(t,b){'
              'if(t)document.documentElement.dataset.theme=t;'
              'else delete document.documentElement.dataset.theme;'
              'try{localStorage.setItem("iris-theme",t)}catch(e){}'
              'document.querySelectorAll(".dot").forEach(d=>d.classList.remove("sel"));'
              'b.classList.add("sel")}'
              '(function(){var cur="";try{cur=localStorage.getItem("iris-theme")||""}catch(e){}'
              'var d=document.querySelector(\'.dot[data-t="\'+cur+\'"]\');if(d)d.classList.add("sel")})()'
              '</script>')

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
        def do_POST(self):
            import urllib.parse as U
            if self.path.startswith("/delete/"):
                mid = self.path.split("/delete/", 1)[1].strip("/")
                d = os.path.join(store_dir, mid)
                if "/" not in mid and ".." not in mid and os.path.isdir(d):
                    import shutil; shutil.rmtree(d)
                self.send_response(303)
                self.send_header("Location", "/")
                return self.end_headers()
            if not self.path.startswith("/rename/"):
                self.send_response(404); return self.end_headers()
            mid = self.path.split("/rename/", 1)[1].strip("/")
            length = int(self.headers.get("Content-Length", 0))
            title = U.parse_qs(self.rfile.read(length).decode()).get("title", [""])[0].strip()
            mp = os.path.join(store_dir, mid, "meta.json")
            if title and "/" not in mid and ".." not in mid and os.path.isfile(mp):
                meta = json.load(open(mp))
                meta["title"] = title
                json.dump(meta, open(mp, "w"), indent=2)
            self.send_response(303)
            self.send_header("Location", f"/meeting/{mid}")
            self.end_headers()
        def do_GET(self):
            import urllib.parse as U
            path = U.urlparse(self.path).path
            if path == "/":
                self._active = None
                self._html('<h1 style="margin-top:24px">Meetings</h1>'
                           '<div class=empty>' + mascot(120)
                           + '<div class=t>Pick a meeting</div>'
                           + '<div class=s>from the list, or search across everything - even encrypted notes</div></div>')
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
                           + (rows or '<div class=empty>' + mascot(88, "sleep")
                              + '<div class=t>Nothing found</div>'
                              + '<div class=s>try another word - Iris only searches your own notes</div></div>'))
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
                fresh = 0 < (time.time() - meta.get("created", 0)) < 600
                body = (confetti(mid) if fresh else "")
                if fresh:
                    body += ('<div class=empty style="padding-top:6px">' + mascot(80, "celebrate")
                             + '<div class=t>Meeting saved</div>'
                             + '<div class=s>encrypted, verified, and only on your devices</div></div>')
                body += (f'<h1>{esc(meta.get("title", mid))}</h1><div class=doc-meta>{when} &middot; {mid}</div>'
                        f'<form method=post action="/rename/{mid}" style="margin-bottom:18px">'
                        f'<input name=title placeholder="Rename meeting" style="padding:5px 9px;font-size:13px;border:1px solid var(--border);border-radius:6px;width:220px;background:var(--input-bg);color:var(--text)"> '
                        f'<button style="padding:5px 12px;font-size:13px;border:1px solid var(--border);border-radius:999px;background:var(--input-bg);color:var(--text)">rename</button></form>'
                        f'<form method=post action="/delete/{mid}" onsubmit="return confirm(\'Delete this meeting? Notes and transcript are removed from this device.\')" style="margin-bottom:24px">'
                        f'<button style="padding:5px 12px;font-size:13px;border:1px solid var(--danger-border);border-radius:999px;background:var(--input-bg);color:var(--danger)">delete meeting</button></form>')
                if "notes.md" in texts:
                    body += render_notes_md(texts["notes.md"])
                if "transcript.md" in texts:
                    lines = "<br>".join(render_transcript_line(l) for l in texts["transcript.md"].splitlines())
                    body += (f'<hr class=divider><h2>{heading_icon("transcript")}Transcript</h2>'
                             f'<pre class=transcript>{lines}</pre>')
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
    print(f"Iris UI on http://127.0.0.1:{a.port} (local only - serves decrypted content)")
    HTTPServer(("127.0.0.1", a.port), make_handler(a.store)).serve_forever()
