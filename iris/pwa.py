"""Installable web app (PWA) pieces: manifest, offline shell service worker,
icons, and the in-browser recorder page."""
import json, os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pwa")

MANIFEST = json.dumps({
    "name": "Iris", "short_name": "Iris", "description": "Meeting notes that keep receipts",
    "start_url": "/", "scope": "/", "display": "standalone",
    "background_color": "#fcfbf8", "theme_color": "#3f8f4f",
    "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
              {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
    "shortcuts": [{"name": "Record a meeting", "url": "/record"}, {"name": "New note", "url": "/new"}],
})

# Network first so notes are never stale; falls back to the cached copy when offline.
SW = """const V='iris-v1';
self.addEventListener('install',e=>{self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  const r=e.request;
  if(r.method!=='GET'||new URL(r.url).origin!==location.origin)return;
  e.respondWith(fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(r,c))}return res})
    .catch(()=>caches.match(r).then(m=>m||new Response('<meta charset=utf-8><body style="font-family:system-ui;padding:2em"><h2>Offline</h2><p>Iris cannot reach your server. Notes you opened before are still available.</p>',{headers:{'Content-Type':'text/html'}}))));
});
"""

def asset(name: str):
    p = os.path.join(HERE, name)
    return open(p, "rb").read() if os.path.isfile(p) else None

HEAD_TAGS = ('<link rel=manifest href=/manifest.webmanifest><meta name=theme-color content="#3f8f4f">'
             '<link rel=icon href=/icon-192.png><link rel=apple-touch-icon href=/icon-192.png>'
             '<meta name=apple-mobile-web-app-capable content=yes>')
SW_REGISTER = "<script>if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(function(){})</script>"

RECORD_BODY = """<h1 class=title style="font-size:30px">Record a meeting</h1>
<p class=greet style="text-align:left;margin:0 0 14px">Audio goes to your own Iris server for transcription. Nothing is sent anywhere else.</p>
<input id=rtitle placeholder="Title (optional)" style="width:100%;margin-bottom:12px">
<div style="display:flex;gap:10px;align-items:center">
<button id=rbtn class=btn-green type=button>Start recording</button>
<span id=rtime style="font-variant-numeric:tabular-nums;color:var(--muted)">00:00</span></div>
<p id=rmsg style="color:var(--muted);margin-top:14px"></p>
<script>(function(){
var btn=document.getElementById('rbtn'),msg=document.getElementById('rmsg'),tm=document.getElementById('rtime');
var rec=null,chunks=[],t0=0,tick=null;
function fmt(s){return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}
btn.onclick=async function(){
  if(rec){rec.stop();return}
  if(!navigator.mediaDevices||!window.MediaRecorder){msg.textContent='This browser cannot record. Use Chrome, Edge, Firefox or Safari over https or localhost.';return}
  try{var st=await navigator.mediaDevices.getUserMedia({audio:true})}catch(e){msg.textContent='Microphone blocked: '+e.message+' (needs https or localhost)';return}
  chunks=[];rec=new MediaRecorder(st);
  rec.ondataavailable=function(e){if(e.data.size)chunks.push(e.data)};
  rec.onstop=async function(){
    st.getTracks().forEach(function(t){t.stop()});clearInterval(tick);
    var type=rec.mimeType||'audio/webm';rec=null;btn.disabled=true;btn.textContent='Transcribing...';msg.textContent='Uploading and transcribing. Long meetings take a few minutes.';
    var blob=new Blob(chunks,{type:type});
    try{var r=await fetch('/api/record',{method:'POST',headers:{'Content-Type':type,'X-Iris-Title':encodeURIComponent(document.getElementById('rtitle').value)},body:blob});
      var j=await r.json();if(r.ok){location.href='/meeting/'+j.meeting}else{msg.textContent='Failed: '+(j.error||r.status)+(j.meeting?' (audio kept as '+j.meeting+')':'');btn.disabled=false;btn.textContent='Start recording'}}
    catch(e){msg.textContent='Could not reach the server: '+e.message;btn.disabled=false;btn.textContent='Start recording'}
  };
  rec.start(1000);t0=Date.now();btn.textContent='Stop and save';
  tick=setInterval(function(){tm.textContent=fmt(Math.floor((Date.now()-t0)/1000))},500);
};})()</script>"""
