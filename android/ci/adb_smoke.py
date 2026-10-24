#!/usr/bin/env python3
"""Deterministic adb smoke test for the Iris debug APK. No LLM, no secrets.

Phases:
  A) cold launch on a fresh install - capture which app is foreground
     (investigation lead from Artemis run: permissioncontroller held foreground
     15s+); then grant the runtime dialogs like a user would (tap "While using
     the app").
  B) record 10s, stop, assert UI state transitions and the WAV on disk.
Prints one PASS/FAIL line per check; exits 1 on any FAIL.
Screenshots + UI dumps land in ./smoke-out for artifact upload.
"""
import re, subprocess, sys, time, os

OUT = "smoke-out"
os.makedirs(OUT, exist_ok=True)
PKG = "in.iris.app"
fails = []

def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"CMD-FAIL: {cmd}\n{r.stdout}{r.stderr}")
    return r.stdout + r.stderr

def report(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" - {detail}" if detail else ""))
    if not ok: fails.append(name)

def dump(tag):
    sh("adb shell uiautomator dump /sdcard/ui.xml")
    sh(f"adb pull /sdcard/ui.xml {OUT}/{tag}.xml")
    try: return open(f"{OUT}/{tag}.xml", encoding="utf-8").read()
    except FileNotFoundError: return ""

def shot(tag):
    sh(f"adb shell screencap -p /sdcard/{tag}.png")
    sh(f"adb pull /sdcard/{tag}.png {OUT}/{tag}.png")

def tap_text(xml, text, timeout_s=15):
    """Tap the center of the node whose @text matches; retry until timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % re.escape(text), xml)
        if not m:
            m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*text="%s"' % re.escape(text), xml)
        if m:
            x = (int(m.group(1)) + int(m.group(3))) // 2
            y = (int(m.group(2)) + int(m.group(4))) // 2
            sh(f"adb shell input tap {x} {y}")
            return True
        time.sleep(1.5)
        xml = dump("retry")
    return False

def foreground():
    out = sh("adb shell dumpsys activity activities | grep -i 'ResumedActivity'", check=False)
    return out.strip()[:200]

print("== phase A: cold launch (fresh install) ==")
sh(f"adb shell am start -n {PKG}/.MainActivity")
time.sleep(6)
fg = foreground()
print("foreground after cold launch:", fg)
xmlA = dump("A1-permission")
shot("A1-permission")
report("cold-launch foreground captured", bool(fg), fg[:120])
report("permission dialog foregrounded on fresh install (lead from Artemis run)",
       "permissioncontroller" in fg, fg[:120])

# grant like a user: mic dialog, then possibly notifications dialog
for attempt in range(3):
    if "While using the app" in xmlA:
        tap_text(xmlA, "While using the app"); time.sleep(2)
    elif "Allow" in xmlA:
        tap_text(xmlA, "Allow"); time.sleep(2)
    else:
        break
    xmlA = dump(f"A{attempt+2}-postgrant")

time.sleep(3)
fg2 = foreground()
print("foreground after grants:", fg2)
shot("A3-app")
report("app in foreground after granting dialogs", "iris" in fg2.lower(), fg2[:120])

print("== phase B: record 10s, stop, verify ==")
xmlB = dump("B1-app")
report("Start recording button present", "Start recording" in xmlB)
tap_text(xmlB, "Start recording")
time.sleep(3)
xmlB2 = dump("B2-recording")
shot("B2-recording")
report("status shows recording", "recording" in xmlB2.lower())

time.sleep(10)
tap_text(xmlB2, "Stop recording")
time.sleep(4)
xmlB3 = dump("B3-stopped")
shot("B3-stopped")
report("button back to Start recording after stop", "Start recording" in xmlB3)

lsout = sh(f"adb shell run-as {PKG} ls -l files", check=False)
print("files dir:", lsout.strip()[:300])
m = re.search(r"(\d+)\s+\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s+(meeting-\d+-\d+\.wav)", lsout)
size = int(m.group(1)) if m else 0
report("meeting WAV saved in app files dir", bool(m), (m.group(2) + f" {size}B") if m else lsout.strip()[:120])
# 10s of 16kHz mono 16-bit ~= 320KB; accept >100KB as real audio captured
report("WAV has real audio payload (>100KB)", size > 100_000, f"{size}B")

print("== RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
