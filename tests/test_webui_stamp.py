"""Portable timestamp stamps: %-d/%-I are glibc-only and raise ValueError
on the Windows CRT, which killed every webui page render on Windows
(found on a real Windows 11 PC, 2026-11-04)."""
import os, re, time
from iris import webui

def _expect(t):
    h12 = t.tm_hour % 12 or 12
    ampm = "AM" if t.tm_hour < 12 else "PM"
    return h12, ampm

def test_when():
    ts = 1700000000
    t = time.localtime(ts)
    h12, ampm = _expect(t)
    assert webui._when(ts) == f"{time.strftime('%b', t)} {t.tm_mday}, {h12}:{t.tm_min:02d} {ampm}"

def test_day():
    ts = 1700000000
    t = time.localtime(ts)
    assert webui._day(ts) == f"{time.strftime('%A, %b', t)} {t.tm_mday}"

def test_day_short():
    ts = 1700000000
    t = time.localtime(ts)
    assert webui._day_short(ts) == f"{time.strftime('%a %b', t)} {t.tm_mday}"

def test_when_full():
    ts = 1700000000
    t = time.localtime(ts)
    h12, ampm = _expect(t)
    assert webui._when_full(ts) == f"{time.strftime('%B', t)} {t.tm_mday}, {t.tm_year} at {h12}:{t.tm_min:02d} {ampm}"

def test_midnight_and_noon_edges():
    for ts in (1700000000,):
        t0 = time.localtime(ts)
        midnight = webui._when(time.mktime((t0.tm_year, t0.tm_mon, t0.tm_mday, 0, 5, 0, 0, 0, -1)))
        assert re.search(r"\b12:05 AM$", midnight)
        noon = webui._when(time.mktime((t0.tm_year, t0.tm_mon, t0.tm_mday, 12, 5, 0, 0, 0, -1)))
        assert re.search(r"\b12:05 PM$", noon)

def test_no_glibc_only_strftime_flags():
    src = open(os.path.join(os.path.dirname(webui.__file__), "webui.py")).read()
    assert not re.search(r'strftime\(\s*"[^"]*%-', src)
