# Windows port of scripts/benchmark/run_one.py (no unix 'resource' module).
import sys, time, json, os
REPO = r'D:\iris-test\iris'
sys.path.insert(0, REPO)
os.chdir(REPO)
def _resolve_whisper_cli():
    # v1.9.1 whisper-bin-x64.zip nests binaries under Release\; older or
    # manual layouts may put them at the root. Accept either, else search.
    import glob
    candidates = [r'D:\iris-test\whisper-bin-x64\whisper-cli.exe',
                  r'D:\iris-test\whisper-bin-x64\Release\whisper-cli.exe']
    for c in candidates:
        if os.path.exists(c):
            return c
    hits = glob.glob(r'D:\iris-test\whisper-bin-x64\**\whisper-cli.exe', recursive=True)
    if hits:
        return hits[0]
    sys.exit('whisper-cli.exe not found under D:\\iris-test\\whisper-bin-x64 - re-run windows_setup.ps1')
os.environ['IRIS_WHISPER_CLI'] = _resolve_whisper_cli()
from iris import transcribe as T
audio, model, lang, out, careful = sys.argv[1:6]
t0 = time.time()
raw_out = out.replace('out_', 'raw_')
segs = T.transcribe(audio, model=model, language=lang, raw_out=raw_out,
                    careful=(careful == '1'), allow_unsupported=True)
dt = time.time() - t0
bad = sum(s['text'].count('�') for s in segs)
json.dump({'audio': audio, 'model': model, 'language': lang, 'utf8_replacements': bad,
           'wall_s': round(dt, 1), 'peak_child_mb': -1, 'segments': len(segs), 'segs': segs},
          open(out, 'w'))
print(f"DONE {os.path.basename(model)} {os.path.basename(audio)}: {dt:.0f}s wall, {len(segs)} segs", flush=True)
