"""Local web UI for browsing meetings. Binds 127.0.0.1 only - it serves
DECRYPTED transcripts and notes, so it must never be reachable off the
machine. Design: Notion/Granola/macOS - calm document reading, soft neutrals.

  python3 iris/webui.py --port 8473
"""
import argparse, hmac, html, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iris import store as S
from iris.mascot import mascot
from iris import library as L

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Iris</title>
<!--PWA-->
<script>try{var t=localStorage.getItem("iris-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}</script>
<style>
:root{
  --bg:#fcfbf8; --side:#f4f2ec; --text:#2f2d29; --muted:#76736b; --faint:#a8a49a;
  --border:#e8e5dc; --border-soft:#eeebe3; --accent:#3f8f4f;
  --font:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,"Helvetica Neue",Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --quote-border:#d3d1cb; --pill-ok-bg:#eef7ee; --pill-ok:#2f6b31;
  --input-bg:#ffffff; --active-bg:#e3e3e0; --danger:#b83232; --danger-border:#e5c7c5;
  --accent-soft:#e6f1e3; --ink:#3b2a20; --active-bg:#e9e6dd;
}
[data-theme=blue]{ --accent:#2383e2; --accent-soft:#e7f0fb; }
[data-theme=purple]{ --accent:#6940a5; --accent-soft:#efeaf7; }
[data-theme=orange]{ --accent:#d9730d; --accent-soft:#faebdd; }
[data-theme=pink]{ --accent:#c14c8a; --accent-soft:#f8e9f1; }
[data-theme=red]{ --accent:#d44c47; --accent-soft:#fae9e8; }
@media (prefers-color-scheme: dark){
  :root{
    --bg:#191918; --side:#1f1f1d; --text:#dcdad3; --muted:#a09d94; --faint:#706d65;
    --border:#31302c; --border-soft:#2a2927; --accent:#6bb37a;
    --quote-border:#4a4a47; --pill-ok-bg:#1e2b1e; --pill-ok:#6aaa6f;
    --input-bg:#252525; --active-bg:#373737; --danger:#e08a8a; --danger-border:#5a3535;
    --accent-soft:#1f2e22; --ink:#e9dcc8; --active-bg:#2e2d29;
  }
  [data-theme=blue]{ --accent:#529cca; --accent-soft:#1c2f3d; }
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
.dot[data-t=""]{background:#3f8f4f}.dot[data-t=blue]{background:#2383e2}
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
input,select,button,textarea{font-family:var(--font)}
input{transition:border-color .25s var(--spring),box-shadow .25s var(--spring)}
input:focus{box-shadow:0 0 0 3px var(--accent-soft)}
.bullet,.todo,blockquote,.nav-item,h2,h3,.pill{animation:rise .5s var(--spring) both}
.rise:nth-child(2){animation-delay:.04s}.rise:nth-child(3){animation-delay:.08s}
.rise:nth-child(4){animation-delay:.12s}.rise:nth-child(5){animation-delay:.16s}
.rise:nth-child(6){animation-delay:.2s}.rise:nth-child(7){animation-delay:.24s}
.rise:nth-child(n+8){animation-delay:.28s}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
/* motion and type taken from hssn.me: one ease, short staggered fade-up with a touch of blur, hairlines, mono eyebrows */
@keyframes stagger-in{from{opacity:0;transform:translateY(6px);filter:blur(2px)}to{opacity:1;transform:none;filter:none}}
.doc>*{opacity:0;animation:stagger-in .5s var(--spring) forwards;animation-delay:calc(var(--i,0)*70ms + 40ms)}
.doc>*:nth-child(1){--i:0}.doc>*:nth-child(2){--i:1}.doc>*:nth-child(3){--i:2}.doc>*:nth-child(4){--i:3}.doc>*:nth-child(5){--i:4}.doc>*:nth-child(n+6){--i:5}
.nav-item{opacity:0;animation:stagger-in .45s var(--spring) forwards;animation-delay:calc(var(--n,0)*35ms + 80ms)}
.nav-item:nth-of-type(2){--n:1}.nav-item:nth-of-type(3){--n:2}.nav-item:nth-of-type(4){--n:3}.nav-item:nth-of-type(5){--n:4}.nav-item:nth-of-type(n+6){--n:5}
.nav-item,.folder,.cta,.cta2,.mi,.pinbtn{transition:transform .18s var(--spring),background .18s ease,color .18s ease,box-shadow .18s ease}
.cta:hover,.cta2:hover{transform:translateY(-2px)}.cta:active{transform:none}
.nav-item:hover{transform:translateX(2px)}
.nav-sec,.eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint)}
.title{letter-spacing:-.04em;font-weight:680}
h2.big{letter-spacing:-.02em}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
body{margin:0;font:16px/1.65 var(--font);-webkit-font-smoothing:antialiased;
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
.nav-sec{font-size:11px;font-weight:600;color:var(--faint);padding:14px 10px 4px;letter-spacing:.08em}
.folder{display:flex;align-items:center;gap:6px;padding:5px 10px;border-radius:6px;color:var(--text);text-decoration:none;font-size:14px}
.folder:hover{background:var(--active-bg)}.folder.on{background:var(--active-bg);font-weight:500}
.folder .chev{font-size:10px;color:var(--faint);width:10px}.folder .count{margin-left:auto;font-size:11.5px;color:var(--faint)}
.indent{margin-left:14px;border-left:1px solid var(--border-soft);padding-left:4px}
.newfolder input{width:100%;border:0;background:transparent;font-size:13px;padding:5px 10px;color:var(--muted)}
.newfolder input:focus{background:var(--input-bg);color:var(--text);outline:0;border-radius:6px}
.newnote{margin:0 6px 4px}.newnote button{width:100%;text-align:left;padding:7px 10px;border:0;border-radius:6px;
  background:transparent;color:var(--text);font-size:14px;font-weight:500}
.newnote button:hover{background:var(--active-bg)}
.title{display:block;width:100%;border:0;background:transparent;font-size:38px;font-weight:700;letter-spacing:-.6px;color:var(--text);padding:2px 0;margin:6px 0 4px;outline:0;font-family:inherit}
.title:focus{box-shadow:none}.title::placeholder{color:var(--faint)}
.crumb{font-size:13px;color:var(--muted)}.crumb a{color:var(--muted);text-decoration:none}.crumb a:hover{color:var(--text)}
.props{display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-size:13px;color:var(--muted);margin-bottom:22px}
.propform{display:inline-block;margin:0}
.props select,.pinbtn{font-size:13px;color:var(--muted);background:transparent;border:1px solid transparent;border-radius:6px;padding:3px 8px;font-family:inherit}
.props select:hover,.pinbtn:hover{background:var(--active-bg)}.pinbtn.on{color:#c98b1d}
.more{position:relative}.more summary{list-style:none;cursor:pointer;padding:3px 8px;border-radius:6px}.more summary:hover{background:var(--active-bg)}
.more summary::-webkit-details-marker{display:none}
.menu{position:absolute;z-index:5;left:0;top:28px;background:var(--input-bg);border:1px solid var(--border);border-radius:8px;padding:4px;box-shadow:0 6px 24px rgba(0,0,0,.12)}
.menu .mi{display:block;width:100%;text-align:left;border:0;background:transparent;color:var(--text);padding:6px 14px;font-size:13px;border-radius:6px}.menu .mi:hover{background:var(--active-bg)}
.menu .danger{border:0;background:transparent;color:var(--danger);padding:6px 14px;font-size:13px;border-radius:6px;white-space:nowrap}.menu .danger:hover{background:var(--active-bg)}
#slash{position:absolute;z-index:6;min-width:230px;background:var(--input-bg);border:1px solid var(--border);border-radius:10px;padding:4px;box-shadow:0 8px 28px rgba(0,0,0,.14)}
.slash-item{display:flex;justify-content:space-between;gap:18px;padding:6px 10px;border-radius:6px;font-size:14px;cursor:pointer}
.slash-item span{color:var(--faint);font-family:var(--mono);font-size:12px}
.slash-item.on,.slash-item:hover{background:var(--active-bg)}
.edwrap{position:relative}
#ed{width:100%;min-height:160px;border:0;resize:none;background:transparent;color:var(--text);font:inherit;font-size:16px;line-height:1.65;outline:0;padding:0;box-shadow:none}
.edmeta{display:flex;justify-content:space-between;font-size:12px;color:var(--faint);margin-top:6px}
.ghost{border:1px solid var(--border);background:transparent;color:var(--muted);border-radius:999px;padding:4px 14px;font-size:13px;margin:10px 0}
.ghost:empty{display:none}
a.wikilink{color:var(--accent);text-decoration:none;border-bottom:1px dashed color-mix(in srgb,var(--accent) 50%,transparent)}
a.wikilink:hover{border-bottom-style:solid}
.wikilink.missing{color:var(--muted);border-bottom:1px dashed var(--border)}
.tdrawer{margin-top:28px;border-top:1px solid var(--border-soft);padding-top:14px}
.tdrawer summary{cursor:pointer;font-size:15px;font-weight:600;color:var(--muted);list-style:none}
.tdrawer summary::-webkit-details-marker{display:none}
.tdrawer summary .icon{width:18px;height:18px;vertical-align:-3px;margin-right:7px;color:var(--accent)}
[hidden]{display:none!important}
.inline{display:inline-block;margin:0 6px 18px 0}
.inline input{padding:5px 9px;font-size:13px;border:1px solid var(--border);border-radius:6px;background:var(--input-bg);color:var(--text)}
.inline button{padding:5px 12px;font-size:13px;border:1px solid var(--border);border-radius:999px;background:var(--input-bg);color:var(--text)}
.inline .danger{border-color:var(--danger-border);color:var(--danger)}.inline .primary{background:var(--accent);border-color:var(--accent);color:#fff}
#qs{position:fixed;inset:0;z-index:50;background:rgba(0,0,0,.28);display:flex;justify-content:center;padding-top:14vh}
#qs[hidden]{display:none}
.qsbox{width:min(520px,92vw);height:fit-content;background:var(--bg);border:1px solid var(--border);border-radius:12px;box-shadow:0 18px 60px rgba(0,0,0,.25);overflow:hidden}
#qsin{width:100%;border:0;border-bottom:1px solid var(--border-soft);padding:14px 16px;font-size:16px;background:transparent;color:var(--text);outline:0;box-shadow:none}
.qsi{padding:9px 16px;font-size:14.5px;cursor:pointer}.qsi.on,.qsi:hover{background:var(--active-bg)}.qsnone{padding:14px 16px;color:var(--faint);font-size:14px}
.speaker{cursor:pointer}
.dragging{opacity:.4}
.dropbefore{box-shadow:0 -2px 0 var(--accent)}
h2.big{font-size:26px;margin-top:28px}
.todo.done>span:nth-child(2){text-decoration:line-through;color:var(--faint)}
.box.on{background:var(--accent);border-color:var(--accent)}
.num{margin:4px 0}.num .n{color:var(--muted);display:inline-block;min-width:22px}
code{font-family:var(--mono);font-size:.9em;background:var(--side);border:1px solid var(--border-soft);border-radius:4px;padding:1px 5px}
del{color:var(--faint)}
.lang{font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;padding:1px 6px;border-radius:999px;background:var(--accent-soft);color:var(--accent);margin-right:2px}
.recent{max-width:560px;margin:34px auto 0;text-align:left}
.card{display:block;padding:12px 14px;border:1px solid var(--border);border-radius:10px;margin-bottom:10px;text-decoration:none;color:var(--text);background:var(--input-bg)}
.card:hover{border-color:var(--accent)}.card .nav-title{font-size:15px}
.nav-item{display:block;padding:6px 10px;border-radius:6px;color:var(--text);text-decoration:none;margin-bottom:1px}
.nav-item:hover{background:var(--active-bg)}
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
.stats{display:flex;gap:12px;justify-content:center;margin:18px auto 0;max-width:560px}
.stat{flex:1;background:var(--side);border:1px solid var(--border-soft);border-radius:10px;
  padding:12px 14px;text-align:center}
.stat .n{font-size:22px;font-weight:600;color:var(--text)}
.stat .l{font-size:11.5px;color:var(--faint);margin-top:1px}
.greet{font-size:13px;color:var(--muted);text-align:center;margin-top:26px}
.mascot{display:block;margin:26px auto 10px;cursor:pointer;transform-origin:50% 92%;overflow:visible}
.mascot.happy{animation:sway 5s 1.6s ease-in-out infinite}
@keyframes sway{0%,100%{transform:rotate(-1.4deg)}50%{transform:rotate(1.4deg)}}
.mascot.sleep{animation:breathe 4.5s 1.6s ease-in-out infinite}
@keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.025)}}
.mascot.celebrate{animation:settle .9s cubic-bezier(.34,1.56,.64,1) both}
@keyframes settle{from{transform:translateY(8px) scale(.94);opacity:0}to{transform:none;opacity:1}}
.mascot .stem path{stroke-dasharray:1;stroke-dashoffset:0;animation:draw .7s cubic-bezier(.4,0,.2,1) both}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.mascot .leaf{transform-box:view-box;animation:unfurl .65s calc(.35s + var(--d,0s)) cubic-bezier(.34,1.56,.64,1) both}
@keyframes unfurl{from{transform:scale(0) rotate(-24deg);opacity:0}to{transform:none;opacity:1}}
.mascot .bloom{transform-box:fill-box;transform-origin:50% 50%;animation:pop .8s .85s cubic-bezier(.34,1.56,.64,1) both}
@keyframes pop{from{transform:scale(0) rotate(-50deg)}to{transform:none}}
.mascot .sparkles{animation:twinkle 1.6s 1.6s ease-in-out infinite}
@keyframes twinkle{0%,100%{opacity:1}50%{opacity:.25}}
.mascot.wink{animation:boing .5s cubic-bezier(.34,1.56,.64,1)}
@keyframes boing{30%{transform:scale(1.07,.93)}60%{transform:scale(.97,1.05)}}
@media (prefers-reduced-motion:reduce){.mascot,.mascot *{animation:none!important}}
.empty{text-align:center;color:var(--muted);padding:28px 12px 8px}
.empty .t{font-size:15px;color:var(--text);font-weight:500;margin-top:6px}
.empty .s{font-size:13px;margin-top:2px}
pre.transcript{background:var(--side);border:1px solid var(--border-soft);border-radius:8px;
  padding:18px 20px;font:13px/1.8 ui-monospace,"SF Mono",Menlo,monospace;white-space:pre-wrap;color:#4a4844}
.back{color:var(--muted);text-decoration:none;font-size:13.5px}
.back:hover{color:var(--text)}
.divider{border:none;border-top:1px solid var(--border-soft);margin:40px 0}
.menubtn{display:none;float:right;font-size:13px;color:var(--muted);border:1px solid var(--border);border-radius:999px;padding:3px 12px;cursor:pointer;margin-top:2px}
#navtoggle{position:absolute;opacity:0;pointer-events:none}
@media (max-width:900px){
  .layout{flex-direction:column}
  .sidebar{width:100%;height:auto;position:static;border-right:none;border-bottom:1px solid var(--border-soft)}
  .doc{padding:32px 22px 80px}
  h1{font-size:25px}
  .title{font-size:30px}
  .menubtn{display:inline-block}
  .sidebar .nav,.sidebar .themes,.sidebar .newnote{display:none}
  #navtoggle:checked ~ .nav{display:block}
  #navtoggle:checked ~ .themes{display:flex}
  #navtoggle:checked ~ .newnote{display:block}
  .sidebar{padding:12px 14px;display:block}
  .brand{display:inline-block;padding-bottom:8px}
}
</style>"""

def esc(t): return html.escape(t or "")

def load_meta_safe(store_dir: str, mid: str):
    """meta.json as dict, or None when missing/corrupt (one bad meeting must
    not take the whole UI down)."""
    try:
        return json.load(open(os.path.join(store_dir, mid, "meta.json")))
    except (OSError, json.JSONDecodeError):
        return None

def read_meeting_texts(store_dir: str, mid: str):
    """Plaintext dict, or None when the meeting is encrypted and the local key
    can't open it (wrong/missing key)."""
    from iris import crypto as C
    try:
        return (S.decrypt_meeting(store_dir, mid) if S.is_encrypted(store_dir, mid)
                else {n: open(os.path.join(store_dir, mid, n)).read()
                      for n in S.PLAINTEXT_FILES if os.path.exists(os.path.join(store_dir, mid, n))})
    except C.CryptoError:
        return None

GRAPH_JS = """<script>(function(){
var g=window.__graph,cv=document.getElementById('graph');if(!g||!cv)return;
var ctx=cv.getContext('2d'),W,H,dpr=window.devicePixelRatio||1;
function size(){W=cv.clientWidth;H=520;cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0)}
size();window.addEventListener('resize',function(){size()});
var ns=g.nodes.map(function(n,i){n.x=W/2+Math.cos(i*2.4)*Math.min(W,H)/3*(0.4+0.6*((i*37%10)/10));n.y=H/2+Math.sin(i*2.4)*Math.min(W,H)/3*(0.4+0.6*((i*53%10)/10));n.vx=0;n.vy=0;return n});
var byId={};ns.forEach(function(n){byId[n.id]=n});
var es=g.edges.map(function(e){return{a:byId[e.from],b:byId[e.to]}}).filter(function(e){return e.a&&e.b});
function tick(){
 ns.forEach(function(n){n.vx+=(W/2-n.x)*0.002;n.vy+=(H/2-n.y)*0.002;
  ns.forEach(function(m){if(m!==n){var dx=n.x-m.x,dy=n.y-m.y,d2=dx*dx+dy*dy+40;if(d2<16000){var f=900/d2;n.vx+=dx*f/60;n.vy+=dy*f/60}}})});
 es.forEach(function(e){var dx=e.b.x-e.a.x,dy=e.b.y-e.a.y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(d-110)*0.004;e.a.vx+=dx/d*f*d;e.a.vy+=dy/d*f*d;e.b.vx-=dx/d*f*d;e.b.vy-=dy/d*f*d});
 ns.forEach(function(n){if(n!==drag){n.x+=Math.max(-6,Math.min(6,n.vx));n.y+=Math.max(-6,Math.min(6,n.vy))}n.vx*=0.82;n.vy*=0.82;n.x=Math.max(30,Math.min(W-30,n.x));n.y=Math.max(20,Math.min(H-20,n.y))});
 ctx.clearRect(0,0,W,H);
 var st=getComputedStyle(document.documentElement);
 ctx.strokeStyle=st.getPropertyValue('--border')||'#ddd';ctx.lineWidth=1;
 es.forEach(function(e){ctx.beginPath();ctx.moveTo(e.a.x,e.a.y);ctx.lineTo(e.b.x,e.b.y);ctx.stroke()});
 ctx.font='12px ui-sans-serif,system-ui,sans-serif';ctx.textAlign='center';
 ns.forEach(function(n){ctx.beginPath();ctx.arc(n.x,n.y,7,0,7);ctx.fillStyle=st.getPropertyValue('--accent')||'#22c55e';ctx.fill();
  ctx.fillStyle=st.getPropertyValue('--text')||'#222';var t=n.title.length>26?n.title.slice(0,25)+'\u2026':n.title;ctx.fillText(t,n.x,n.y+22)});
 requestAnimationFrame(tick)}
var drag=null;
cv.addEventListener('pointerdown',function(e){var r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
 drag=null;ns.forEach(function(n){if((n.x-x)*(n.x-x)+(n.y-y)*(n.y-y)<140)drag=n});if(drag)cv.setPointerCapture(e.pointerId)});
cv.addEventListener('pointermove',function(e){if(!drag)return;var r=cv.getBoundingClientRect();drag.x=e.clientX-r.left;drag.y=e.clientY-r.top;drag.vx=0;drag.vy=0});
cv.addEventListener('pointerup',function(e){if(!drag)return;var r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,d=drag;drag=null;
 if(Math.abs(d.x-x)<4&&Math.abs(d.y-y)<4)location.href='/meeting/'+encodeURIComponent(d.id)});
tick();})()</script>"""

EDITOR_JS = """<script>(function(){
var ed=document.getElementById('ed'),t=document.getElementById('title'),sv=document.getElementById('saved');
var tg=document.getElementById('toggle'),vw=document.getElementById('view'),eb=document.getElementById('edit');
if(!ed||!t)return;
function fit(){ed.style.height='auto';ed.style.height=Math.max(160,ed.scrollHeight)+'px'}
function post(url,data){return fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','X-Fetch':'1'},body:new URLSearchParams(data)})}
var tm,dirty=false;
function save(){dirty=false;sv.textContent='Saving...';post('/notes/'+ed.dataset.mid,{text:ed.value}).then(function(){sv.textContent='Saved'}).catch(function(){sv.textContent='Not saved - retrying'})}
ed.addEventListener('input',function(){fit();dirty=true;sv.textContent='Editing...';clearTimeout(tm);tm=setTimeout(save,500)});
ed.addEventListener('keydown',function(e){if(e.key==='Tab'){e.preventDefault();var s=ed.selectionStart;ed.setRangeText('  ',s,ed.selectionEnd,'end');ed.dispatchEvent(new Event('input'))}
 if(e.key==='Enter'){var v=ed.value,s=ed.selectionStart,ls=v.lastIndexOf('\\n',s-1)+1,line=v.slice(ls,s),m=line.match(/^(\\s*)(- \\[[ x]\\] |- |\\d+\\. )/);
  if(m){e.preventDefault();if(line.trim()===m[2].trim()){ed.setRangeText('',ls,s,'end')}else{var nx=m[2].match(/^\\d+/)?(parseInt(m[2])+1)+'. ':m[2].replace('[x]','[ ]');ed.setRangeText('\\n'+m[1]+nx,s,s,'end')}ed.dispatchEvent(new Event('input'))}}});
var tt;t.addEventListener('input',function(){clearTimeout(tt);tt=setTimeout(function(){post('/rename/'+t.dataset.mid,{title:t.value||'Untitled'})},400)});
t.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();ed.focus()}});
if(tg)tg.addEventListener('click',function(){if(eb.hidden){vw.hidden=true;eb.hidden=false;tg.textContent='Done';fit();ed.focus()}else{if(dirty){clearTimeout(tm);save()}setTimeout(function(){location.reload()},120)}});
if(!ed.value&&eb&&!eb.hidden)setTimeout(function(){ed.focus()},50);
window.addEventListener('load',fit);fit();
})()</script>"""

SPEAKER_JS = """<script>(function(){
document.addEventListener('click',function(e){var c=e.target.closest&&e.target.closest('.speaker');if(!c)return;
var old=c.dataset.spk,nm=prompt('Who is '+old+'?',old.indexOf('Speaker ')===0?'':old);
if(!nm||!nm.trim()||nm.trim()===old)return;var mid=location.pathname.split('/').pop();
fetch('/speaker/'+mid,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({old:old,new:nm.trim()})})
.then(function(r){if(r.ok)location.reload();else r.text().then(function(t){alert(t)})})})})()</script>"""

EDITOR_FMT_JS = "<script>" + open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static_editor.js")).read() + """
(function(){var ed=document.getElementById('ed');if(!ed)return;
var menu=document.createElement('div');menu.id='slash';menu.hidden=true;ed.parentNode.insertBefore(menu,ed.nextSibling);
var items=[],sel=0,ctx=null;
function fire(){ed.dispatchEvent(new Event('input'))}
function close(){menu.hidden=true;ctx=null}
function render(){menu.innerHTML=items.map(function(b,i){return '<div class="slash-item'+(i===sel?' on':'')+'" data-i="'+i+'">'+b.k+'<span>'+b.p.trim()+'</span></div>'}).join('')}
function place(){var lh=parseFloat(getComputedStyle(ed).lineHeight)||26;var n=ed.value.slice(0,ed.selectionStart).split(String.fromCharCode(10)).length;
 menu.style.top=(ed.offsetTop+n*lh+4)+'px'}
function update(){var q=irisSlashQuery(ed.value,ed.selectionStart);if(!q){close();return}
 items=irisBlocks(q.q);if(!items.length){close();return}ctx=q;sel=0;render();place();menu.hidden=false}
function choose(i){var r=irisApplyBlock(ed.value,ed.selectionStart,ctx.from,items[i]);ed.value=r.v;ed.setSelectionRange(r.c,r.c);close();fire()}
ed.addEventListener('input',update);
ed.addEventListener('keydown',function(e){
 if(!menu.hidden){
  if(e.key==='ArrowDown'){e.preventDefault();e.stopImmediatePropagation();sel=(sel+1)%items.length;render();return}
  if(e.key==='ArrowUp'){e.preventDefault();e.stopImmediatePropagation();sel=(sel-1+items.length)%items.length;render();return}
  if(e.key==='Enter'||e.key==='Tab'){e.preventDefault();e.stopImmediatePropagation();choose(sel);return}
  if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();close();return}}
 if((e.ctrlKey||e.metaKey)&&!e.shiftKey&&!e.altKey){var m={b:'**',i:'*',e:'`'}[e.key.toLowerCase()];
  if(m){e.preventDefault();var r=irisWrap(ed.value,ed.selectionStart,ed.selectionEnd,m);ed.value=r.v;ed.setSelectionRange(r.s,r.e);fire()}}
},true);
menu.addEventListener('mousedown',function(e){var it=e.target.closest('.slash-item');if(it){e.preventDefault();choose(+it.dataset.i)}});
ed.addEventListener('blur',function(){setTimeout(close,120)});
})()</script>"""

def confetti(mid: str) -> str:
    """One-time celebrate burst the first time a fresh (<10 min) meeting is opened."""
    return (f"<script>(function(){{try{{if(localStorage.getItem('iris-party-{mid}'))return;"
            "localStorage.setItem('iris-party-" + mid + "','1')}catch(e){}"
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
            "setTimeout(function(el){return function(){el.remove()}}(d),3200)}})();</script>")

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
    lab = label or "Speaker " + str(n + 1)
    return (f'<span class="speaker spk{n % N_SPEAKER_COLORS}" data-spk="{esc(lab)}" '
            f'title="Click to name this speaker">{esc(lab)}</span>')

def lang_pill(text: str) -> str:
    """'<hinglish> kal hai' -> small pill + text. Plain text passes through."""
    import re
    m = re.match(r"^<(hinglish|hi|[a-z]{2,3})> (.*)$", text)
    if not m:
        return esc(text)
    tag, rest = m.groups()
    return f'<span class="lang lang-{tag if tag in ("hinglish", "hi") else "x"}">{esc(tag)}</span> {esc(rest)}'

def render_transcript_line(line: str) -> str:
    """[mm:ss] Speaker N: text / [mm:ss] Name: text -> timestamp + chip + text"""
    import re
    m = re.match(r"^\[(\d\d:\d\d)\] (?:(Speaker \d+)|([A-Za-z\u0900-\u097F][\w\u0900-\u097F -]{0,29})): (.*)$", line)
    if m:
        ts, numbered, name, text = m.groups()
        label = numbered or name
        idx = (int(numbered.split()[1]) - 1) if numbered else (sum(label.encode()) % N_SPEAKER_COLORS)
        chip = speaker_chip(idx, label)
        return f'<span style="color:var(--faint)">{ts}</span>  {chip}{lang_pill(text)}'
    m2 = re.match(r"^\[(\d\d:\d\d)\] (.*)$", line)
    if m2:
        return f'<span style="color:var(--faint)">{m2.group(1)}</span>  {esc(m2.group(2))}'
    return esc(line)

def inline_md(t: str, link_resolver=None) -> str:
    """Escape first, then turn **bold**, *italic*, `code`, ~~strike~~ and [[wiki links]] into tags.
    link_resolver(target) -> (url, exists) makes [[target]] a link; without one [[..]] stays text."""
    import re
    t = esc(t)
    if link_resolver:
        def _wiki(m):
            target, label = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
            url, exists = link_resolver(target)
            if not exists:
                return f'<span class="wikilink missing">{esc(label)}</span>'
            return f'<a class=wikilink href="{url}">{esc(label)}</a>'
        t = re.sub(r"\[\[([^\[\]|]{1,120})(?:\|([^\[\]]{1,120}))?\]\]", _wiki, t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", t)
    return t

def render_notes_md(md: str, skip_title: bool = True, link_resolver=None) -> str:
    import re
    def inline_md_r(t):
        return inline_md(t, link_resolver)
    out = []
    first = True
    for line in md.splitlines():
        if first and line.strip():
            first = False
            if skip_title and line.startswith("# "):
                continue  # generated notes: page title already shown
        if line.startswith("# "):
            out.append(f"<h2 class=big>{inline_md_r(line[2:])}</h2>")
        elif line.startswith("## "):
            t = line[3:]
            out.append(f"<h2>{heading_icon(t)}{inline_md_r(t)}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{inline_md_r(line[4:])}</h3>")
        elif line.strip() in ("---", "***"):
            out.append("<hr class=divider>")
        elif line.startswith("  > ") or line.startswith("> "):
            body = line.split("> ", 1)[1]
            m = re.match(r'^"(.*)"\s*\[(\d\d:\d\d)\]$', body)
            if m:
                out.append(f'<blockquote>&ldquo;{esc(m.group(1))}&rdquo; <span class=ts>{m.group(2)}</span></blockquote>')
            else:
                out.append(f"<blockquote>{inline_md_r(body)}</blockquote>")
        elif re.match(r"^\s*- \[[xX]\] ", line):
            out.append(f'<div class="todo done"><span class="box on"></span><span>{inline_md_r(line.split("] ", 1)[1])}</span></div>')
        elif re.match(r"^\s*- \[ \] ", line):
            out.append(f'<div class=todo><span class=box></span><span>{inline_md_r(line.split("] ", 1)[1])}</span></div>')
        elif re.match(r"^\s*- ", line):
            depth = (len(line) - len(line.lstrip())) // 2
            out.append(f'<div class=bullet style="margin-left:{depth * 20}px">{inline_md_r(line.lstrip()[2:])}</div>')
        elif re.match(r"^\d+\. ", line):
            n, rest = line.split(". ", 1)
            out.append(f'<div class=num><span class=n>{n}.</span> {inline_md_r(rest)}</div>')
        elif line.startswith("_integrity"):
            m = re.search(r"(\d+)/(\d+)", line)
            label = f"{m.group(1)}/{m.group(2)} claims verified" if m else esc(line)
            out.append(f'<p><span class=pill>{label}</span></p>')
        elif line.strip():
            out.append(f"<p>{inline_md_r(line)}</p>")
    return "\n".join(out)

def meeting_nav(store_dir: str, mid: str) -> str:
    """Newer/older neighbor links for the meeting page footer."""
    ids = sorted(S.list_meetings(store_dir))
    if mid not in ids or len(ids) < 2:
        return ""
    i = ids.index(mid)
    older = ids[i - 1] if i > 0 else None
    newer = ids[i + 1] if i < len(ids) - 1 else None
    def lbl(other, arrow):
        if not other:
            return "<span style=\"opacity:.35\"></span>"
        t = esc(_title_in(store_dir, other))
        return f'<a class=back href="/meeting/{other}">{arrow} {t}</a>'
    return ('<div style="display:flex;justify-content:space-between;margin:26px 0 4px;'
            'font-size:12.5px">'
            + lbl(older, "&larr;") + lbl(newer, "&rarr;") + "</div>")

def _title_in(store_dir: str, mid: str) -> str:
    try:
        return json.load(open(os.path.join(store_dir, mid, "meta.json"))).get("title", mid)
    except Exception:
        return mid

def _nav_item(mid, meta, active, group=""):
    integ = meta.get("integrity") or {}
    iv = f' &middot; {integ.get("passed")}/{integ.get("checked")} verified' if integ else ""
    when = time.strftime("%b %-d, %-I:%M %p", time.localtime(meta.get("created", 0)))
    cls = "nav-item active" if mid == active else "nav-item"
    kind = "note" if meta.get("kind") == "note" else ("locked" if meta.get("encrypted") else "")
    tail = f' &middot; {kind}' if kind else ""
    return (f'<a class="{cls}" href="/meeting/{mid}" data-mid="{mid}" data-group="{group}" draggable="true">'
            f'<div class=nav-title>{esc(meta.get("title", mid))}</div>'
            f'<div class=nav-meta>{when}{tail}{iv}</div></a>')

def _day_label(ts: float) -> str:
    d = time.strftime("%Y-%m-%d", time.localtime(ts))
    if d == time.strftime("%Y-%m-%d"): return "Today"
    if d == time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)): return "Yesterday"
    return time.strftime("%A, %b %-d", time.localtime(ts))

def _preview(store_dir: str, mid: str, meta: dict) -> str:
    if meta.get("encrypted"):
        return "Encrypted"
    try:
        for line in open(os.path.join(store_dir, mid, "notes.md")).read().splitlines():
            raw = line.strip()
            if raw.startswith("#"): continue  # headings make poor previews
            t = raw.lstrip("-> [x]").strip() if raw[:1] in "->" else raw
            if t: return t[:110]
    except OSError:
        pass
    return ""

def _recent_cards(store_dir: str, mids: list, limit: int = 8) -> str:
    rows = []
    for m in mids:
        meta = load_meta_safe(store_dir, m)
        if meta: rows.append((m, meta))
    rows.sort(key=lambda t: (not t[1].get("pinned"), -t[1].get("created", 0)))
    if not rows: return ""
    out, last = "<div class=recent>", None
    for m, meta in rows[:limit]:
        label = "Pinned" if meta.get("pinned") else _day_label(meta.get("created", 0))
        if label != last:
            out += f'<div class=nav-sec>{label}</div>'; last = label
        pv = _preview(store_dir, m, meta)
        out += (f'<a class=card href="/meeting/{m}"><div class=nav-title>{esc(meta.get("title", m))}</div>'
                + (f'<div class=nav-meta>{esc(pv)}</div>' if pv else "") + '</a>')
    return out + "</div>"

def _switcher(metas) -> str:
    """Ctrl/Cmd+K: jump to any note by typing part of its title."""
    data = json.dumps([{"id": m, "t": x.get("title", m)} for m, x in metas]).replace("<", "\\u003c")
    return ("<div id=qs hidden><div class=qsbox><input id=qsin placeholder='Jump to a note...' autocomplete=off>"
            "<div id=qslist></div></div></div><script>(function(){var D=" + data + ";"
            "var b=document.getElementById('qs'),i=document.getElementById('qsin'),l=document.getElementById('qslist'),sel=0,cur=[];"
            "function draw(){var q=i.value.toLowerCase();cur=D.filter(function(n){return n.t.toLowerCase().indexOf(q)!==-1}).slice(0,8);sel=Math.min(sel,Math.max(0,cur.length-1));"
            "l.innerHTML=cur.map(function(n,k){var d=document.createElement('div');d.textContent=n.t;return '<div class=\"qsi'+(k===sel?' on':'')+'\" data-id=\"'+n.id+'\">'+d.innerHTML+'</div>'}).join('')||'<div class=qsnone>No notes match</div>'}"
            "function open(){b.hidden=false;i.value='';sel=0;draw();i.focus()}function close(){b.hidden=true}"
            "document.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();b.hidden?open():close()}"
            "else if(!b.hidden){if(e.key==='Escape')close();else if(e.key==='ArrowDown'){e.preventDefault();sel=Math.min(sel+1,cur.length-1);draw()}"
            "else if(e.key==='ArrowUp'){e.preventDefault();sel=Math.max(sel-1,0);draw()}"
            "else if(e.key==='Enter'&&cur[sel]){location.href='/meeting/'+cur[sel].id}}});"
            "i.addEventListener('input',function(){sel=0;draw()});"
            "b.addEventListener('mousedown',function(e){var it=e.target.closest('.qsi');if(it)location.href='/meeting/'+it.dataset.id;else if(e.target===b)close()});})()</script>")

def sidebar(store_dir: str, active: str | None, active_folder: str | None = None) -> str:
    metas = []
    for mid in S.list_meetings(store_dir, reverse=True):
        meta = load_meta_safe(store_dir, mid)
        if meta is not None:
            metas.append((mid, meta))
    folders = L.list_folders(store_dir)
    fids = {f["id"] for f in folders}
    pinned = sorted([(m, x) for m, x in metas if x.get("pinned")], key=lambda t: L.order_key(t[1]))
    loose = [(m, x) for m, x in metas if x.get("folder") not in fids]
    sec = lambda t: f'<div class=nav-sec>{t}</div>'
    out = ""
    if pinned:
        out += sec("Pinned") + "".join(_nav_item(m, x, active, "pinned") for m, x in pinned)
    out += sec("Folders")
    for f in folders:
        inside = sorted([(m, x) for m, x in metas if x.get("folder") == f["id"]], key=lambda t: L.order_key(t[1]))
        open_ = f["id"] == active_folder or any(m == active for m, _ in inside)
        out += (f'<a class="folder{" on" if f["id"] == active_folder else ""}" href="/folder/{f["id"]}" data-fid="{f["id"]}" data-group="folders" draggable="true">'
                f'<span class=chev>{"&#9662;" if open_ else "&#9656;"}</span>{esc(f["name"])}'
                f'<span class=count>{len(inside)}</span></a>')
        if open_:
            out += '<div class=indent>' + "".join(_nav_item(m, x, active, f["id"]) for m, x in inside) + '</div>'
    out += ('<form class=newfolder method=post action="/folders/new">'
            '<input name=name placeholder="+ New folder" maxlength=60 autocomplete=off></form>')
    out += sec("Notes") + ("".join(_nav_item(m, x, active) for m, x in loose) or "")
    if not metas:
        out += ('<div class=empty>' + mascot(72, "sleep")
                + '<div class=t>No meetings yet</div>'
                + '<div class=s>record one and Iris will keep it safe</div></div>')
    return ('<input type=checkbox id=navtoggle><label for=navtoggle class=menubtn>Menu</label>'
            '<div class=brand>Iris<span id=tagline>private meeting notes</span></div>'
            '<script>(function(){var t=["private meeting notes","your meetings, your machines",'
            '"your audio stays on your devices","notes that keep receipts","local first, always yours"];'
            'var i=Math.floor(Math.random()*t.length),el=document.getElementById("tagline");'
            'if(el)el.textContent=t[i]})()</script>'
            '<form class=searchbox method=get action="/search">'
            '<input name=q placeholder="Search meetings"></form>'
            '<form method=post action="/new" class=newnote>'
            + (f'<input type=hidden name=folder value="{esc(active_folder)}">' if active_folder else "")
            + '<button>+ New note</button></form>'
            + '<a class=folder href="/record" style="margin:2px 0 6px"><span class=chev></span>Record a meeting</a>'
            + _switcher(metas)
            + '<div class=nav>' + out + '<a class=folder href="/recap"><span class=chev></span>Recap</a><a class=folder href="/graph"><span class=chev></span>Graph</a><a class=folder href="/cloud"><span class=chev></span>Cloud sync</a><a class=folder href="/trash"><span class=chev></span>Trash</a></div>'
            + '<div class=themes><span class=lbl>Theme</span>'
            + ''.join(f'<button class=dot data-t="{t}" title="{t or "blue"}" '
                      f'onclick="pickTheme(\'{t}\',this)"></button>'
                      for t in ("", "blue", "purple", "orange", "pink", "red"))
            + '</div>'
            + '<script>(function(){var drag=null;'
              'document.addEventListener("dragstart",function(e){var a=e.target.closest&&e.target.closest("[data-group]");if(!a)return;drag=a;a.classList.add("dragging");e.dataTransfer.effectAllowed="move";try{e.dataTransfer.setData("text/plain","x")}catch(x){}});'
              'document.addEventListener("dragend",function(){if(drag)drag.classList.remove("dragging");document.querySelectorAll(".dropbefore").forEach(function(n){n.classList.remove("dropbefore")});drag=null});'
              'document.addEventListener("dragover",function(e){if(!drag)return;var t=e.target.closest&&e.target.closest("[data-group]");'
              'if(!t||t===drag||t.dataset.group!==drag.dataset.group)return;e.preventDefault();'
              'document.querySelectorAll(".dropbefore").forEach(function(n){n.classList.remove("dropbefore")});t.classList.add("dropbefore")});'
              'document.addEventListener("drop",function(e){if(!drag)return;var t=e.target.closest&&e.target.closest("[data-group]");'
              'if(!t||t===drag||t.dataset.group!==drag.dataset.group)return;e.preventDefault();'
              't.parentNode.insertBefore(drag,t);var g=drag.dataset.group,sib=Array.prototype.filter.call(t.parentNode.children,function(n){return n.dataset&&n.dataset.group===g});'
              'var isF=g==="folders";var ids=sib.map(function(n){return isF?n.dataset.fid:n.dataset.mid});'
              'fetch("/reorder/"+(isF?"folders":"notes"),{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams({ids:ids.join(",")})}).then(function(){location.reload()})});})()</script>'
            + '<script>document.addEventListener("click",function(e){'
              'var m=e.target.closest&&e.target.closest(".mascot");'
              'if(m){m.classList.remove("wink");void m.offsetWidth;m.classList.add("wink")}});</script>'
            + '<script>document.addEventListener("keydown",function(e){'
              'if(e.key==="/"&&!/INPUT|TEXTAREA/.test(document.activeElement.tagName)){'
              'e.preventDefault();var q=document.querySelector(".searchbox input");if(q)q.focus()}'
              'if(e.key==="Escape")document.activeElement.blur()});'
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
    from iris import pwa as W
    return (PAGE.replace('<!--PWA-->', W.HEAD_TAGS) + inner + W.SW_REGISTER).encode()

def make_handler(store_dir: str, token: str = "", backend: str = "ollama"):
    class H(BaseHTTPRequestHandler := __import__("http.server", fromlist=["BaseHTTPRequestHandler"]).BaseHTTPRequestHandler):
        def _html(self, body: str, status: int = 200):
            data = page(f'<div class=layout><nav class=sidebar>{sidebar(store_dir, self._active, self._folder)}</nav>'
                        f'<main class=content><div class=doc>{body}</div></main></div>')
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        _active = None
        _folder = None
        def do_POST(self):
            import urllib.parse as U
            if self.path.startswith("/delete/"):
                mid = self.path.split("/delete/", 1)[1].strip("/")
                d = os.path.join(store_dir, mid)
                L.trash_note(store_dir, mid)
                self.send_response(303)
                self.send_header("Location", "/")
                return self.end_headers()
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
            form = {k: v[0] for k, v in U.parse_qs(raw).items()}
            def go(loc):
                self.send_response(303); self.send_header("Location", loc); self.end_headers()
            def ok_mid(m):
                return bool(m) and "/" not in m and ".." not in m and os.path.isfile(os.path.join(store_dir, m, "meta.json"))
            parts = self.path.strip("/").split("/")
            if self.path in ("/cloud/save", "/cloud/sync", "/cloud/forget", "/cloud/auto"):
                from iris import cloud as CL
                try:
                    if self.path == "/cloud/save":
                        CL.save(store_dir, form.get("server", ""), form.get("token", ""), form.get("transcripts") == "1")
                        msg = "Saved."
                    elif self.path == "/cloud/auto":
                        CL.set_auto(store_dir, form.get("auto") == "1")
                        msg = "Auto-sync is on." if form.get("auto") == "1" else "Auto-sync is off. Use Sync now when you want to."
                    elif self.path == "/cloud/forget":
                        CL.forget(store_dir); msg = "Disconnected. Notes already on the cloud stay there until you remove them on the site."
                    else:
                        r = CL.sync_now(store_dir)
                        msg = f"Synced: {r['pushed']} sent, {r['unchanged']} unchanged, {r['pulled']} received."
                except Exception as e:
                    msg = f"Could not sync: {e}"
                return go("/cloud?m=" + U.quote(msg))
            if self.path == "/new":
                fid = form.get("folder") or None
                return go("/meeting/" + L.new_note(store_dir, form.get("title", ""), fid))
            if parts[0] == "folders":
                if len(parts) == 2 and parts[1] == "new":
                    try: f = L.create_folder(store_dir, form.get("name", ""))
                    except ValueError: return go("/")
                    return go("/folder/" + f["id"])
                if len(parts) == 3 and parts[2] == "rename":
                    L.rename_folder(store_dir, parts[1], form.get("name", ""))
                    return go("/folder/" + parts[1])
                if len(parts) == 3 and parts[2] == "delete":
                    L.delete_folder(store_dir, parts[1]); return go("/")
            if len(parts) == 2 and parts[0] == "duplicate" and ok_mid(parts[1]):
                return go("/meeting/" + L.duplicate_note(store_dir, parts[1]))
            if len(parts) == 2 and parts[0] == "restore":
                L.restore_note(store_dir, parts[1]); return go("/trash")
            if self.path == "/trash/empty":
                L.purge_trash(store_dir, older_than_days=0); return go("/trash")
            if len(parts) == 2 and parts[0] == "reorder" and parts[1] in ("folders", "notes"):
                ids = [i for i in form.get("ids", "").split(",") if i]
                if parts[1] == "folders": L.reorder_folders(store_dir, ids)
                else: L.reorder_notes(store_dir, ids)
                self.send_response(204); return self.end_headers()
            if len(parts) == 2 and parts[0] == "speaker" and ok_mid(parts[1]):
                try:
                    n = L.rename_speaker(store_dir, parts[1], form.get("old", ""), form.get("new", ""))
                except ValueError as e:
                    self.send_response(400); self.end_headers(); self.wfile.write(str(e).encode()); return
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"changed": n}).encode()); return
            if len(parts) == 2 and parts[0] in ("pin", "unpin", "move", "notes") and ok_mid(parts[1]):
                mid = parts[1]
                if parts[0] == "notes":
                    L.save_notes(store_dir, mid, form.get("text", ""))
                    self.send_response(204); return self.end_headers()
                if parts[0] == "move":
                    try: L.move(store_dir, mid, form.get("folder") or None)
                    except ValueError: pass
                else:
                    L.set_pinned(store_dir, mid, parts[0] == "pin")
                return go(form.get("next") or "/meeting/" + mid)
            if not self.path.startswith("/rename/"):
                self.send_response(404); return self.end_headers()
            mid = self.path.split("/rename/", 1)[1].strip("/")
            title = form.get("title", "").strip()
            mp = os.path.join(store_dir, mid, "meta.json")
            if title and "/" not in mid and ".." not in mid and os.path.isfile(mp):
                meta = json.load(open(mp))
                meta["title"] = title[:120]  # sidebar + h1 layouts assume sane titles
                json.dump(meta, open(mp, "w"), indent=2)
            if self.headers.get("X-Fetch"):
                self.send_response(204); return self.end_headers()
            self.send_response(303)
            self.send_header("Location", f"/meeting/{mid}")
            self.end_headers()
        def do_GET(self):
            import urllib.parse as U
            path = U.urlparse(self.path).path
            if path == "/":
                self._active = None
                mids = S.list_meetings(store_dir, reverse=True)
                n_enc = n_pass = n_checked = 0
                for m in mids:
                    mt = load_meta_safe(store_dir, m) or {}
                    n_enc += 1 if mt.get("encrypted") else 0
                    ig = mt.get("integrity") or {}
                    n_pass += ig.get("passed", 0); n_checked += ig.get("checked", 0)
                hour = time.localtime().tm_hour
                greet = ("Good night" if hour < 5 else "Good morning" if hour < 12
                         else "Good afternoon" if hour < 17 else "Good evening")
                stats = ('<div class=stats>'
                         f'<div class=stat><div class=n>{len(mids)}</div><div class=l>meeting{"s" if len(mids)!=1 else ""}</div></div>'
                         f'<div class=stat><div class=n>{n_enc}</div><div class=l>encrypted</div></div>'
                         f'<div class=stat><div class=n>{n_pass}/{n_checked}</div><div class=l>claims verified</div></div>'
                         '</div>') if mids else ""
                recent = _recent_cards(store_dir, mids)
                self._html(f'<div class=greet>{greet}.</div>'
                           '<div class=empty style="padding-top:2px">' + mascot(120)
                           + '<div class=t>Pick a meeting</div>'
                           + '<div class=s>from the list, or search across everything - even encrypted notes</div>'
                           + stats + '</div>' + recent)
            elif path == "/search":
                q = U.parse_qs(U.urlparse(self.path).query).get("q", [""])[0].strip()
                self._active = None
                if not q:
                    return self._html("<h1>Search</h1><p class=doc-meta>Type something in the search box.</p>")
                hits = S.search(store_dir, q)
                def _title(mid):
                    try:
                        return json.load(open(os.path.join(store_dir, mid, "meta.json"))).get("title", mid)
                    except Exception:
                        return mid
                rows = "".join(
                    f'<div style="margin-bottom:14px"><a class=nav-title href="/meeting/{h["meeting"]}">{esc(_title(h["meeting"]))}</a>'
                    f'<div class=nav-meta>{esc(h["file"])}</div><p style="margin-top:2px">{esc(h["line"][:200])}</p></div>'
                    for h in hits)
                self._html(f'<h1>Search</h1><p class=doc-meta>{len(hits)} result(s) for &ldquo;{esc(q)}&rdquo;</p>'
                           + (rows or '<div class=empty>' + mascot(88, "sleep")
                              + '<div class=t>Nothing found</div>'
                              + '<div class=s>try another word - Iris only searches your own notes</div></div>'))
            elif path.startswith("/folder/"):
                fid = path.split("/folder/", 1)[1].strip("/")
                fl = [f for f in L.list_folders(store_dir) if f["id"] == fid]
                if not fl:
                    self._html("<p>folder not found</p>", status=404); return
                self._active, self._folder = None, fid
                f = fl[0]
                notes = [(m, load_meta_safe(store_dir, m)) for m in S.list_meetings(store_dir, reverse=True)]
                notes = [(m, x) for m, x in notes if x and x.get("folder") == fid]
                notes.sort(key=lambda t: not t[1].get("pinned"))
                cards = "".join(_nav_item(m, x, None).replace('class="nav-item"', 'class="card"') for m, x in notes)
                self._html(
                    f'<h1>{esc(f["name"])}</h1><div class=doc-meta>{len(notes)} note(s)</div>'
                    f'<form method=post action="/folders/{fid}/rename" class=inline>'
                    f'<input name=name value="{esc(f["name"])}" maxlength=60> <button>rename</button></form>'
                    f'<form method=post action="/new" class=inline><input type=hidden name=folder value="{fid}">'
                    f'<button class=primary>+ New note here</button></form>'
                    f'<form method=post action="/folders/{fid}/delete" class=inline '
                    f'onsubmit="return confirm(\'Delete this folder? Its notes are kept.\')">'
                    f'<button class=danger>delete folder</button></form>'
                    + (cards or '<div class=empty>' + mascot(88, "sleep")
                       + '<div class=t>Nothing in this folder yet</div>'
                       + '<div class=s>make a note here, or move one in from its page</div></div>'))
            elif path == "/cloud":
                from iris import cloud as CL
                self._active = None
                st = CL.status(store_dir)
                m = U.parse_qs(U.urlparse(self.path).query).get("m", [""])[0]
                last = _day_label(st["last"]) if st["last"] else "never"
                self._html("<h1>Iris Cloud</h1><div class=doc-meta>Notes only. Your audio never leaves this device"
                           + (", and transcripts stay here too." if not st["transcripts"] else "; transcripts are included because you turned that on.")
                           + "</div>" + (f"<p class=card>{esc(m)}</p>" if m else "")
                           + (f'<p>Linked to <b>{esc(st["server"])}</b>. Last sync: {last}.</p>'
                              '<form method=post action="/cloud/sync" class=inline><button>Sync now</button></form> '
                              '<form method=post action="/cloud/forget" class=inline><button class=danger>Disconnect</button></form>'
                              '<form method=post action="/cloud/auto" style="margin-top:12px"><input type=hidden name=auto value="' + ("0" if st["auto"] else "1") + '">'
                              '<span style="font-size:13px">Auto-sync after each meeting: <b>' + ("on" if st["auto"] else "off") + '</b></span> <button>Turn ' + ("off" if st["auto"] else "on") + '</button></form>' if st["linked"] else
                              "<p>Make a token on your Iris Cloud account page, then paste it here.</p>")
                           + '<form method=post action="/cloud/save" style="display:flex;flex-direction:column;gap:8px;max-width:420px;margin-top:18px">'
                             f'<input name=server value="{esc(st["server"])}" aria-label="Server">'
                             '<input name=token type=password placeholder="Sync token" autocomplete=off aria-label="Token">'
                             f'<label style="font-size:13px"><input type=checkbox name=transcripts value=1 {"checked" if st["transcripts"] else ""}> Also send transcripts (the cloud only keeps them if you allow it in Account)</label>'
                             '<button>Save</button></form>')
            elif path == "/recap":
                from iris import recap as RC, links as LK
                self._active = None
                entries = []
                for m2 in S.list_meetings(store_dir):
                    meta2 = load_meta_safe(store_dir, m2)
                    if meta2 is None:
                        continue
                    texts2 = read_meeting_texts(store_dir, m2)
                    if texts2 is None:   # locked: the recap never decrypts what the key cannot open
                        continue
                    notes2 = texts2.get("notes.md", "")
                    entries.append((meta2.get("title") or m2, meta2.get("created", 0), notes2,
                                    len(LK.extract(notes2))))
                r = RC.summarize(entries)
                def esc2(t): return esc(t)
                body = ('<h1>Weekly recap</h1><div class=doc-meta>Last 7 days, generated when you opened this page. '
                        'Action items below are extracted from your notes, not confirmed as outstanding. '
                        'Locked notes are not included.</div>')
                body += f'<h2>{len(r["meetings"])} note{"s" if len(r["meetings"]) != 1 else ""}</h2>'
                for m3 in r["meetings"]:
                    when2 = time.strftime("%a %b %-d", time.localtime(m3["created"]))
                    body += f'<div class=bullet>{esc2(m3["title"])} <span style="color:var(--muted);font-size:12.5px">{when2}</span></div>'
                if r["decisions"]:
                    body += f"<h2>{heading_icon('decisions')}Decisions</h2>"
                    for d in r["decisions"]:
                        body += f'<div class=bullet>{esc2(d["text"])} <span style="color:var(--muted);font-size:12.5px">- {esc2(d["source"])}</span></div>'
                if r["actions"]:
                    body += f"<h2>{heading_icon('action items')}Action items</h2>"
                    for a in r["actions"]:
                        cls = "todo done" if a["done"] else "todo"
                        box = "box on" if a["done"] else "box"
                        body += (f'<div class="{cls}"><span class="{box}"></span><span>{esc2(a["text"])}</span>'
                                 f' <span style="color:var(--muted);font-size:12.5px">- {esc2(a["source"])}</span></div>')
                if r["link_count"]:
                    body += f'<p style="color:var(--muted);font-size:13px">{r["link_count"]} [[link]]{"s" if r["link_count"] != 1 else ""} written this week. <a class=wikilink href="/graph">Open the graph</a></p>'
                if not r["meetings"]:
                    body += '<div class=empty>' + mascot(72, "sleep") + '<div class=t>Nothing this week</div><div class=s>New notes will show up here.</div></div>'
                self._html(body)
            elif path == "/graph":
                from iris import links as LK
                self._active = None
                g = LK.graph(store_dir)
                data = json.dumps(g)
                empty = (not g["edges"])
                self._html('<h1>Note graph</h1><div class=doc-meta>'
                           + (f'{len(g["nodes"])} notes, {len(g["edges"])} links. Drag nodes, click one to open it.' if not empty
                              else 'No links yet. Write [[another note\'s title]] in a note to connect them.')
                           + '</div><canvas id=graph style="width:100%;height:520px;border:1px solid var(--border);border-radius:12px;margin-top:14px"></canvas>'
                           + '<script>window.__graph=' + data.replace("</", "<\\/") + ';</script>' + GRAPH_JS)
            elif path == "/trash":
                self._active = None
                items = L.list_trash(store_dir)
                rows = "".join(
                    f'<div class=card style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><div class=nav-title>{esc(t["title"])}</div>'
                    f'<div class=nav-meta>deleted {_day_label(t["trashed_at"])}</div></div>'
                    f'<form method=post action="/restore/{t["id"]}" class=inline style="margin:0"><button>Restore</button></form></div>'
                    for t in items)
                empty = ('<form method=post action="/trash/empty" class=inline '
                         'onsubmit="return confirm(\'Permanently delete everything in Trash?\')">'
                         '<button class=danger>Empty Trash</button></form>') if items else ""
                self._html(f'<h1>Trash</h1><div class=doc-meta>Notes here are removed for good after 30 days.</div>' + empty
                           + (rows or '<div class=empty>' + mascot(88, "sleep") + '<div class=t>Trash is empty</div></div>'))
            elif path == "/ask":
                from iris import ask as A
                q = U.parse_qs(U.urlparse(self.path).query).get("q", [""])[0].strip()
                self._active = None
                if not q:
                    return self._html("<h1>Ask</h1><p class=doc-meta>Ask a question, e.g. /ask?q=what did we decide about retention</p>")
                hits = A.ask(store_dir, q)
                rows = "".join(
                    f'<div style="margin-bottom:14px"><a class=nav-title href="/meeting/{h["meeting"]}">{esc(h["title"])}</a>'
                    f'<div class=nav-meta>at {esc(h["at"])}</div><p style="margin-top:2px">&ldquo;{esc(h["quote"])}&rdquo;</p></div>'
                    for h in hits)
                self._html(f'<h1>Ask</h1><p class=doc-meta>{esc(q)}</p>'
                           + (rows or '<div class=empty>' + mascot(88, "sleep")
                              + '<div class=t>Nothing in your meetings answers that</div>'
                              + '<div class=s>Iris only quotes what was said, so it stays quiet when nothing matches</div></div>'))
            elif path.startswith("/raw/"):
                rest = path.split("/raw/", 1)[1].strip("/")
                parts = rest.split("/", 1)
                mid = parts[0]
                fname = parts[1] if len(parts) > 1 else ""
                if ("/" in mid or ".." in mid or fname not in S.PLAINTEXT_FILES
                        or not os.path.isdir(os.path.join(store_dir, mid))):
                    self._html("<p>not found</p>", status=404); return
                texts = read_meeting_texts(store_dir, mid)
                if texts is None:
                    self._html("<p>this meeting is locked on this device</p>", status=403); return
                if fname not in texts:
                    self._html("<p>not found</p>", status=404); return
                body_b = texts[fname].encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{mid}-{fname}"')
                self.send_header("Content-Length", str(len(body_b)))
                self.end_headers()
                self.wfile.write(body_b)
            elif path.startswith("/meeting/"):
                mid = path.split("/meeting/", 1)[1].strip("/")
                self._active = mid
                if "/" in mid or ".." in mid or not os.path.isdir(os.path.join(store_dir, mid)):
                    self._html("<p>not found</p>", status=404); return
                meta = load_meta_safe(store_dir, mid)
                if meta is None:
                    self._html("<p>this meeting's metadata is unreadable</p>", status=500); return
                texts = read_meeting_texts(store_dir, mid)
                if texts is None:
                    self._active = mid
                    self._html('<div class=empty>' + mascot(72, "sleep")
                               + '<div class=t>This meeting is locked</div>'
                               + '<div class=s>the key that sealed it is not on this device</div></div>')
                    return
                when = time.strftime("%B %-d, %Y at %-I:%M %p", time.localtime(meta.get("created", 0)))
                fresh = 0 < (time.time() - meta.get("created", 0)) < 600
                body = (confetti(mid) if fresh else "")
                if fresh:
                    body += ('<div class=empty style="padding-top:6px">' + mascot(124, "celebrate")
                             + '<div class=t>Meeting saved</div>'
                             + '<div class=s>' + ('encrypted and verified' if meta.get("encrypted") else 'verified')
                             + ', saved on this device. Audio never leaves it.</div></div>')
                lock = ' &middot; <span style="color:var(--pill-ok)">encrypted at rest</span>' if meta.get("encrypted") else ""
                fl = L.list_folders(store_dir)
                cur = meta.get("folder")
                crumb = ""
                if cur and any(f["id"] == cur for f in fl):
                    fname = [f["name"] for f in fl if f["id"] == cur][0]
                    crumb = f'<div class=crumb><a href="/folder/{cur}">{esc(fname)}</a> / </div>'
                    self._folder = cur
                opts = '<option value="">No folder</option>' + "".join(
                    f'<option value="{f["id"]}"{" selected" if f["id"] == cur else ""}>{esc(f["name"])}</option>' for f in fl)
                pin = bool(meta.get("pinned"))
                wc = L.word_count(texts.get("notes.md", ""))
                edited_label = (f' &middot; edited {_day_label(meta["edited"]).lower()}' if meta.get("edited") else "") \
                    + (f' &middot; {wc} word{"s" if wc != 1 else ""}' if wc else "")
                body += (crumb
                    + f'<input id=title class=title value="{esc(meta.get("title", mid))}" maxlength=120 '
                      f'placeholder="Untitled" aria-label="Title" data-mid="{mid}">'
                    + f'<div class=props><span>{when}{lock}{edited_label}</span>'
                      f'<form method=post action="/move/{mid}" class=propform><select name=folder onchange="this.form.submit()" aria-label="Folder">{opts}</select></form>'
                      f'<form method=post action="/{"unpin" if pin else "pin"}/{mid}" class=propform>'
                      f'<button class="pinbtn{" on" if pin else ""}" title="{"Unpin" if pin else "Pin to top"}">{"&#9733; Pinned" if pin else "&#9734; Pin"}</button></form>'
                      f'<details class=more><summary>&middot;&middot;&middot;</summary><div class=menu>'
                      f'<form method=post action="/duplicate/{mid}"><button class=mi>Duplicate</button></form>'
                      f'<form method=post action="/delete/{mid}" onsubmit="return confirm(\'Move this note to Trash? You can restore it for 30 days.\')">'
                      f'<button class=danger>Delete</button></form></div></details></div>')
                notes_txt = texts.get("notes.md", "")
                is_note = meta.get("kind") == "note" or not notes_txt.strip()
                from iris import links as LK
                def _resolve(target):
                    m2 = LK.resolve(store_dir, target)
                    return (f"/meeting/{m2}", True) if m2 else ("#", False)
                body += (f'<div id=view{" hidden" if is_note else ""}>{render_notes_md(notes_txt, skip_title=meta.get("kind") != "note", link_resolver=_resolve) if notes_txt.strip() else ""}</div>'
                         f'<div id=edit class=edwrap{"" if is_note else " hidden"}>'
                         f'<textarea id=ed data-mid="{mid}" spellcheck=true placeholder="Write notes. # heading, - list, - [ ] task, > quote">{esc(notes_txt)}</textarea>'
                         f'<div class=edmeta><span id=saved>Saved</span><span>Markdown. Saved on this device only.</span></div></div>'
                         f'<button id=toggle class=ghost>{"Done" if is_note and notes_txt.strip() else ("Edit notes" if not is_note else "")}</button>'
                         + EDITOR_JS + EDITOR_FMT_JS)
                if "transcript.md" in texts:
                    lines = "<br>".join(render_transcript_line(l) for l in texts["transcript.md"].splitlines())
                    body += (f'<p style="font-size:12.5px"><a class=back href="/raw/{mid}/notes.md">download notes.md</a> &middot; <a class=back href="/raw/{mid}/transcript.md">download transcript.md</a></p>'
                         f'<details class=tdrawer{"" if is_note and False else (" open" if not notes_txt.strip() else "")}><summary>{heading_icon("transcript")}Transcript</summary>'
                             f'<pre class=transcript>{lines}</pre></details>' + SPEAKER_JS)
                backs = LK.backlinks(store_dir, mid)
                if backs:
                    body += ('<details class=drawer style="margin-top:22px"><summary>Linked from (' + str(len(backs)) + ')</summary>'
                             + "".join(f'<div style="margin:6px 0"><a class=wikilink href="/meeting/{b}">{esc(t)}</a></div>' for b, t in backs)
                             + '</details>')
                body += meeting_nav(store_dir, mid)
                self._html(body)
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a): pass

    # ---- installable web app + in-browser recorder + optional access token ----
    from iris import pwa as W
    import http.cookies as _ck, urllib.parse as _up
    _get, _post = H.do_GET, H.do_POST

    def _send(self, code, ctype, data, extra=()):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in extra: self.send_header(k, v)
        self.end_headers(); self.wfile.write(data)

    def _allowed(self):
        if not token: return True
        q = _up.parse_qs(_up.urlparse(self.path).query)
        if hmac.compare_digest(q.get("t", [""])[0], token):
            clean = _up.urlparse(self.path).path or "/"
            self.send_response(303); self.send_header("Location", clean)
            self.send_header("Set-Cookie", f"iris_t={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000")
            self.end_headers(); return False
        c = _ck.SimpleCookie(self.headers.get("Cookie", ""))
        if c.get("iris_t") and hmac.compare_digest(c["iris_t"].value, token): return True
        _send(self, 401, "text/html; charset=utf-8", b"<meta charset=utf-8><body style='font-family:system-ui;padding:2em'><h2>Iris</h2><p>Open the link with your access token (?t=...).</p>")
        return False

    def _guard(self):
        """Stop other websites from driving this local app. A page you have open elsewhere can post forms to
        127.0.0.1 (CSRF) or point its own hostname at 127.0.0.1 (DNS rebinding). Reject both.
        On a network bind the access token is the gate, so only the Origin rule applies."""
        host = (_up.urlparse("//" + (self.headers.get("Host") or "")).hostname or "").lower()
        if not token and host not in ("127.0.0.1", "localhost", "::1"):
            _send(self, 421, "text/plain", b"wrong host"); return False
        origin = self.headers.get("Origin")
        if origin and origin != "null" and _up.urlparse(origin).netloc != (self.headers.get("Host") or ""):
            _send(self, 403, "text/plain", b"cross-site request refused"); return False
        if origin == "null":
            _send(self, 403, "text/plain", b"cross-site request refused"); return False
        return True

    def gated_get(self):
        if not self._guard(): return
        path = _up.urlparse(self.path).path
        if path == "/manifest.webmanifest": return _send(self, 200, "application/manifest+json", W.MANIFEST.encode())
        if path == "/sw.js": return _send(self, 200, "text/javascript", W.SW.encode(), [("Service-Worker-Allowed", "/")])
        if path in ("/icon-192.png", "/icon-512.png"):
            data = W.asset(path[1:])
            return _send(self, 200, "image/png", data) if data else _send(self, 404, "text/plain", b"")
        if not self._allowed(): return
        if path == "/record":
            self._active = None; self._folder = None
            return self._html(W.RECORD_BODY.replace("btn-green", "primary"))
        _get(self)

    def gated_post(self):
        if not self._guard(): return
        if not self._allowed(): return
        if _up.urlparse(self.path).path == "/api/record":
            import json as _j
            from iris.pipeline import process_audio, PipelineError
            size = int(self.headers.get("Content-Length", 0) or 0)
            if size < 1000 or size > 500 * 1024 * 1024:
                return _send(self, 400, "application/json", b'{"error":"audio missing, too small or too large"}')
            ctype = self.headers.get("Content-Type", "audio/webm")
            ext = "mp4" if "mp4" in ctype else "ogg" if "ogg" in ctype else "webm"
            title = _up.unquote(self.headers.get("X-Iris-Title", ""))
            try:
                out = process_audio(store_dir, self.rfile.read(size), title, backend, "web-recorder", ext)
                return _send(self, 200, "application/json", _j.dumps(out).encode())
            except PipelineError as e:
                return _send(self, 500, "application/json", _j.dumps({"error": str(e), "meeting": e.meeting}).encode())
        _post(self)

    H._guard = _guard
    H.do_GET, H.do_POST, H._allowed = gated_get, gated_post, _allowed
    return H

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=os.environ.get("IRIS_STORE", "store"))
    ap.add_argument("--port", type=int, default=8473)
    ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to reach it from other devices (then set --token)")
    ap.add_argument("--token", default=os.environ.get("IRIS_UI_TOKEN", ""), help="require ?t=TOKEN on first visit")
    ap.add_argument("--backend", default=os.environ.get("IRIS_BACKEND", "ollama"), choices=["ollama", "ultramarine"])
    a = ap.parse_args()
    if a.host != "127.0.0.1" and not a.token:
        sys.exit("refusing to serve decrypted notes on the network without --token")
    from http.server import ThreadingHTTPServer
    print(f"Iris on http://{a.host}:{a.port}" + (" (token required)" if a.token else " (local only)"))
    ThreadingHTTPServer((a.host, a.port), make_handler(a.store, a.token, a.backend)).serve_forever()
