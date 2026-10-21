from convo import watch

def test_start_event_message():
    t, b = watch.format_event({"type": "meeting_start", "app": "Zoom", "signals": []})
    assert "Zoom" in t and "manual" in b   # consent stays explicit

def test_end_event_message():
    t, b = watch.format_event({"type": "meeting_end", "app": "Google Meet"})
    assert "ended" in t.lower() and "ingest" in b

def test_notify_never_crashes_headless():
    assert "hello" in watch.notify("hello", "world")
