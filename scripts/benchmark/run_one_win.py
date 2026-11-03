# Windows port of scripts/benchmark/run_one.py (no unix 'resource' module).
import sys, time, json, os
REPO = r'D:\iris-test\iris'
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ['IRIS_WHISPER_CLI'] = r'D:\iris-test\whisper-bin-x64\whisper-cli.exe'
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
