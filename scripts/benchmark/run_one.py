#!/usr/bin/env python3
# Runs one benchmark leg through the repo product path (iris.transcribe) and
# writes raw segments + wall time + peak child RSS to a JSON file.
import sys, time, json, resource, os
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
os.chdir(REPO)
from iris import transcribe as T
audio, model, lang, out = sys.argv[1:5]
t0 = time.time()
raw_out = out.replace("out_", "raw_")
segs = T.transcribe(audio, model=model, language=lang, raw_out=raw_out)
dt = time.time() - t0
peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
bad = sum(s["text"].count("\ufffd") for s in segs)
json.dump({"audio": audio, "model": model, "language": lang, "utf8_replacements": bad, "wall_s": round(dt, 1),
           "peak_child_mb": round(peak, 1), "segments": len(segs), "segs": segs}, open(out, "w"))
print(f"DONE {os.path.basename(model)} {os.path.basename(audio)}: {dt:.0f}s wall, peak {peak:.0f}MB, {len(segs)} segs", flush=True)
