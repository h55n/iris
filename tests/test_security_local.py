"""Security checks for the local app and the self-host relay."""
import json, os, subprocess, sys, tempfile, threading, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, HTTPServer
import pytest
from iris import webui, store as S, sync_server


def _serve(handler, port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _req(url, method="GET", data=None, headers=None):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


@pytest.fixture(scope="module")
def local():
    d = tempfile.mkdtemp()
    mid = S.new_meeting(d, "Secret")
    S.write_text(d, mid, "notes.md", "# Secret\n- x")
    srv = _serve(webui.make_handler(d), 18601)
    yield f"http://127.0.0.1:18601", mid, d
    srv.shutdown()


def test_normal_requests_still_work(local):
    base, mid, _ = local
    assert _req(base + "/")[0] == 200
    assert _req(base + "/cloud")[0] == 200
    assert _req(base + "/cloud/save", "POST", b"server=https://x.test/sync&token=t",
                {"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})[0] in (200, 303)


def test_cross_site_post_is_refused(local):
    base, mid, d = local
    for origin in ("https://evil.example", "null", "http://127.0.0.1:9999"):
        code, _ = _req(base + "/cloud/save", "POST", b"server=https://evil.example/sync&token=x",
                       {"Origin": origin, "Content-Type": "application/x-www-form-urlencoded"})
        assert code == 403, origin
        code, _ = _req(base + f"/delete/{mid}", "POST", b"", {"Origin": origin})
        assert code == 403, origin
    assert os.path.isfile(os.path.join(d, mid, "meta.json"))   # nothing was deleted


def test_dns_rebinding_host_is_refused(local):
    base, mid, _ = local
    assert _req(base + "/", headers={"Host": "attacker.example:18601"})[0] == 421
    assert _req(base + "/raw/" + mid + "/notes.md", headers={"Host": "attacker.example"})[0] == 421
    assert _req(base + "/", headers={"Host": "localhost:18601"})[0] == 200


def test_raw_path_traversal_is_refused(local):
    base, _, _ = local
    for p in ("/raw/../../etc/passwd", "/raw/%2e%2e/notes.md", "/raw/x/..%2f..%2fetc%2fpasswd"):
        assert _req(base + p)[0] in (400, 404)


def test_network_bind_needs_token_and_compares_it():
    d = tempfile.mkdtemp()
    srv = _serve(webui.make_handler(d, "s3cret"), 18602)
    try:
        assert _req("http://127.0.0.1:18602/")[0] == 401
        assert _req("http://127.0.0.1:18602/?t=wrong")[0] == 401
        assert _req("http://127.0.0.1:18602/", headers={"Cookie": "iris_t=wrong"})[0] == 401
        assert _req("http://127.0.0.1:18602/", headers={"Cookie": "iris_t=s3cret"})[0] == 200
    finally:
        srv.shutdown()


def test_relay_rejects_bad_token_oversize_and_bad_ids():
    d = tempfile.mkdtemp()
    srv = HTTPServer(("127.0.0.1", 18603), sync_server.make_handler(d, "tok"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        u = "http://127.0.0.1:18603"
        assert _req(u + "/push/m1", "POST", b"{}", {"X-Iris-Token": "no"})[0] == 403
        assert _req(u + "/push/m1", "POST", b"{}", {"X-Iris-Token": "tok", "Content-Length": "9999999999"})[0] == 413
        assert _req(u + "/push/m1", "POST", b"[1]", {"X-Iris-Token": "tok"})[0] == 400
        assert _req(u + "/push/m1", "POST", b"not json", {"X-Iris-Token": "tok"})[0] == 400
        assert _req(u + "/push/..%2Fx", "POST", b"{}", {"X-Iris-Token": "tok"})[0] in (400, 404)
        assert _req(u + "/push/m1", "POST", b'{"audio_b64":"AA"}', {"X-Iris-Token": "tok"})[0] == 400
        assert _req(u + "/push/m1", "POST", b'{"id":"m1","notes":"# ok"}', {"X-Iris-Token": "tok"})[0] == 200
    finally:
        srv.shutdown()


XSS = ['<script>alert(1)</script>', '"><img src=x onerror=alert(1)>', "'><svg onload=alert(1)>", '</title><iframe src=//e>']


def test_notes_rendering_never_emits_user_markup():
    from iris.webui import render_notes_md, render_transcript_line
    for p in XSS + ['[x](javascript:alert(1))', '**<b>x</b>**', '- [ ] <img src=x onerror=1>']:
        for out in (render_notes_md("# T\n\n## Decisions\n- " + p + "\n> \"" + p + "\" 00:01"), render_transcript_line("[00:01] " + p)):
            low = out.lower()
            for tag in ("<script", "<img", "<iframe", "<b>", "<svg onload"):
                assert tag not in low, (p, tag)
            assert "<a " not in low or "javascript:" not in low


def test_titles_and_folder_names_are_escaped_on_every_page():
    from iris import library as L
    d = tempfile.mkdtemp()
    for i, p in enumerate(XSS):
        mid = S.new_meeting(d, p)
        S.write_text(d, mid, "notes.md", "# x\n- " + p)
        S.write_text(d, mid, "transcript.md", "[00:01] " + p)
    fid = L.create_folder(d, XSS[1])["id"]
    L.move(d, S.list_meetings(d)[0], fid)
    srv = _serve(webui.make_handler(d), 18604)
    try:
        base = "http://127.0.0.1:18604"
        pages = ["/folder/" + fid, "/", "/trash", "/cloud", "/search?q=" + urllib.request.quote("<script>alert(1)</script>"), "/ask?q=" + urllib.request.quote(XSS[1])]
        pages += ["/meeting/" + m for m in S.list_meetings(d)]
        for pth in pages:
            code, body = _req(base + pth)
            low = body.lower()
            assert "<script>alert(1)" not in low and "<img src=x onerror" not in low and "<iframe src=//e" not in low and "<svg onload=alert" not in low, pth
    finally:
        srv.shutdown()
