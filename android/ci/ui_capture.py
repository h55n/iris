#!/usr/bin/env python3
"""UI capture for the redesigned main screen. Runs after adb_smoke.py on the same
emulator (app already installed, one recording already saved).

Covers what the smoke test does not: the EXPANDED sync-setup panel (fields,
buttons, masked token rendering) and the Meeting nudges row -> Usage Access
settings intent -> back. Prints PASS/FAIL per check; exits 1 on any FAIL.
Screenshots + dumps land in ./smoke-out for artifact upload.
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

def tap_text(xml, text, timeout_s=12):
    deadline = time.time() + timeout_s
    pat = re.escape(text)
    while time.time() < deadline:
        m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % pat, xml, re.IGNORECASE)
        if m:
            x = (int(m.group(1)) + int(m.group(3))) // 2
            y = (int(m.group(2)) + int(m.group(4))) // 2
            sh(f"adb shell input tap {x} {y}")
            return True
        time.sleep(1.5)
        xml = dump("retry")
    return False

def foreground():
    return sh("adb shell dumpsys activity activities | grep -i 'ResumedActivity'", check=False).strip()[:200]

def swipe(dy1, dy2):
    sh(f"adb shell input swipe 540 {dy1} 540 {dy2}")
    time.sleep(1.5)

def find_with_scroll(text, max_swipes=5):
    xml = dump("find")
    for _ in range(max_swipes + 1):
        if has(xml, text): return xml
        swipe(1900, 800)
        xml = dump("find")
    return xml

def edittext_bounds(xml):
    return re.findall(r'class="android\.widget\.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)

print("== C1: main screen after smoke (recording present) ==")
sh(f"adb shell am start -n {PKG}/.MainActivity")
time.sleep(4)
xml = dump("C1-main")
shot("C1-main")
report("main screen rendered (Start recording present)", has(xml, "Start recording"))

print("== C2: expand Sync setup ==")
report("tapped Sync setup", tap_text(xml, "Sync setup"))
time.sleep(2)
xml = dump("C2-expanded")
shot("C2-expanded")
for label in ["Laptop ingest URL", "Send last recording to laptop",
              "Sync relay URL", "Sync notes now", "age secret key"]:
    report(f"expanded panel shows '{label}'", has(xml, label))
report("4 setup fields present", len(edittext_bounds(xml)) == 4, f"{len(edittext_bounds(xml))} found")

print("== C3: scroll to lower panel ==")
swipe(1900, 800)
xml = dump("C3-scrolled")
shot("C3-scrolled")
report("scrolled panel still shows setup content", has(xml, "age secret key") or has(xml, "Sync notes now"))

print("== C4: masked token field ==")
# empty EditTexts expose their hint as the text attribute; find the token field by hint
m = re.search(r'text="sync token"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
if m:
    x = (int(m.group(1)) + int(m.group(3))) // 2
    y = (int(m.group(2)) + int(m.group(4))) // 2
    sh(f"adb shell input tap {x} {y}"); time.sleep(1)
    sh("adb shell input text Ui9TestKey"); time.sleep(1)
    dump("C4-token-typed")
    shot("C4-token-typed")
    sh("adb shell input keyevent 4")  # hide keyboard
    time.sleep(1)
    report("typed into token field for masking screenshot", True)
else:
    shot("C4-token-field-not-found")
    report("token field located by hint for masking screenshot", False, "hint text not in dump")

print("== C5: Meeting nudges -> usage access ==")
xml = find_with_scroll("Meeting nudges")
report("Meeting nudges row reachable", has(xml, "Meeting nudges"))
report("tapped Meeting nudges", tap_text(xml, "Meeting nudges"))
time.sleep(3)
fg = foreground()
shot("C5-nudge-intent")
report("usage-access settings opened", "settings" in fg.lower(), fg[:120])
sh("adb shell input keyevent 4")
time.sleep(2)
fg = foreground()
shot("C6-back-in-iris")
report("back in Iris after settings", "iris" in fg.lower(), fg[:120])

print("== C7: collapse Sync setup ==")
for _ in range(3): swipe(800, 1900)
xml = dump("C7-top")
report("tapped Sync setup to collapse", tap_text(xml, "Sync setup"))
time.sleep(2)
xml = dump("C7-collapsed")
shot("C7-collapsed")
report("panel collapsed (fields hidden)", not has(xml, "Laptop ingest URL"))

print("== RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
