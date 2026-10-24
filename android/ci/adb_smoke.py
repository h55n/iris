#!/usr/bin/env python3
"""Deterministic adb smoke test for the Iris debug APK. No LLM, no secrets.

Phases:
  A) cold launch on a fresh install - capture which app is foreground
     (investigation lead from Artemis run: permissioncontroller held foreground
     15s+); then grant the runtime dialogs like a user would (tap "While using
     the app").
  B) record 10s, stop, assert UI state transitions and the WAV on disk.

Android renders Button text in ALL CAPS in the accessibility/UI dump
("Start recording" -> "START RECORDING"), while TextView status text keeps its
original case ("recording (local only)"). All button matching here is
case-insensitive; the status assertion uses the exact status string so a
button label can never false-positive it (v1 bug: "START RECORDING" contains
"recording").

Prints one PASS/FAIL line per check; exits 1 on any FAIL.
Screenshots + UI dumps + the pulled WAV land in ./smoke-out for artifact upload.
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

def has(xml, text):
    return text.lower() in xml.lower()

def tap_text(xml, text, timeout_s=15):
    """Tap the center of the node whose @text matches case-insensitively; retry until timeout."""
    deadline = time.time() + timeout_s
    pat = re.escape(text)
    while time.time() < deadline:
        m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % pat, xml, re.IGNORECASE)
        if not m:
            m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*text="%s"' % pat, xml, re.IGNORECASE)
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
    if has(xmlA, "While using the app"):
        tap_text(xmlA, "While using the app"); time.sleep(2)
    elif has(xmlA, "Allow"):
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
report("Start recording button present", has(xmlB, "Start recording"))
report("tapped Start recording", tap_text(xmlB, "Start recording"))
time.sleep(3)
xmlB2 = dump("B2-recording")
shot("B2-recording")
# exact status string from MainActivity ("recording (local only)") - a caps
# button label can never satisfy this
report("status shows exact 'recording (local only)'", "recording (local only)" in xmlB2)
report("button flipped to Stop recording", has(xmlB2, "Stop recording"))

time.sleep(10)
report("tapped Stop recording", tap_text(xmlB2, "Stop recording"))
time.sleep(4)
xmlB3 = dump("B3-stopped")
shot("B3-stopped")
report("button back to Start recording after stop", has(xmlB3, "Start recording"))

# the service broadcasts RECORDING_DONE when the WAV is finalized; the UI must
# confirm the save, not hang on "saving..." (regression: v0.1.0 had no receiver)
deadline = time.time() + 20
saved = False
while time.time() < deadline:
    if has(xmlB3, "saved meeting-"):
        saved = True; break
    time.sleep(2)
    xmlB3 = dump("B3-saved-poll")
shot("B3-saved")
report("status confirms save completion (saved meeting-...)", saved,
       "status left 'saving...'" if saved else "status stuck on 'saving...'")

lsout = sh(f"adb shell run-as {PKG} ls -l /data/data/{PKG}/files", check=False)
print("files dir:", lsout.strip()[:300])
m = re.search(r"(\d+)\s+\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s+(meeting-\d{8}-\d{6}\.wav)", lsout)
size = int(m.group(1)) if m else 0
report("meeting WAV saved in app files dir", bool(m), (m.group(2) + f" {size}B") if m else lsout.strip()[:120])
# 10s of 16kHz mono 16-bit ~= 320KB; accept >100KB as real audio captured
report("WAV has real audio payload (>100KB)", size > 100_000, f"{size}B")

# pull the WAV and verify it is a real RIFF/WAVE file, not a placeholder
if m:
    wav = m.group(2)
    sh(f"adb exec-out run-as {PKG} cat /data/data/{PKG}/files/{wav} > {OUT}/{wav}", check=False)
    try:
        head = open(f"{OUT}/{wav}", "rb").read(12)
        report("pulled WAV has RIFF/WAVE header", head[:4] == b"RIFF" and head[8:12] == b"WAVE", repr(head))
    except FileNotFoundError:
        report("pulled WAV has RIFF/WAVE header", False, "pull failed")

print("== RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
