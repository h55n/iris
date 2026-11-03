#!/usr/bin/env python3
# Windows ingest-server header test: boots the real server on 127.0.0.1:8473
# with a throwaway store and exercises X-Iris-* + legacy X-Convo-* headers
# end to end with the smallest public FLEURS en_us clip (CC BY 4.0).
import glob, json, os, sys, threading, urllib.request, urllib.error
REPO = r'D:\iris-test\iris'
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.setdefault('IRIS_WHISPER_CLI', r'D:\iris-test\whisper-bin-x64\Release\whisper-cli.exe')
from http.server import HTTPServer
from iris.ingest_server import make_handler

STORE = r'D:\iris-test\bench\server-store'
TOKEN = 'testtok'
wavs = sorted(glob.glob(r'D:\iris-test\bench\fleurs\en_us\test\*.wav'), key=os.path.getsize)
assert wavs, 'no FLEURS clips extracted'
WAV = wavs[0]
audio = open(WAV, 'rb').read()
print(f'clip: {os.path.basename(WAV)} ({len(audio)} bytes)', flush=True)

httpd = HTTPServer(('127.0.0.1', 8473), make_handler(STORE, TOKEN, 'ollama'))
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def post(headers):
    req = urllib.request.Request('http://127.0.0.1:8473/ingest', data=audio, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

s, b = post({'X-Iris-Token': 'wrong'})
print(f'T6a bad token -> {s} {b} (expect 403)', flush=True)
assert s == 403, 'bad token not rejected'

s, b = post({'X-Iris-Token': TOKEN, 'X-Iris-Title': 'win header test iris',
             'X-Iris-Language': 'en', 'X-Iris-Careful': '1', 'X-Iris-Allow-Unsupported': '1'})
print(f'T6b X-Iris-* -> {s} {b}', flush=True)
assert s == 200 and b.get('meeting')
meta = json.load(open(os.path.join(STORE, b['meeting'], 'meta.json'), encoding='utf-8'))
print(f"T6b stored title: {meta.get('title')!r} (expect 'win header test iris')", flush=True)
assert meta.get('title') == 'win header test iris'

s, b = post({'X-Convo-Token': TOKEN, 'X-Convo-Title': 'win header test legacy', 'X-Iris-Language': 'en'})
print(f'T6c legacy X-Convo-* -> {s} {b}', flush=True)
assert s == 200 and b.get('meeting')
meta = json.load(open(os.path.join(STORE, b['meeting'], 'meta.json'), encoding='utf-8'))
print(f"T6c stored title: {meta.get('title')!r} (expect 'win header test legacy')", flush=True)
assert meta.get('title') == 'win header test legacy'

httpd.shutdown()
print('T6 PASS', flush=True)
