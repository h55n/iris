"""Wiki-style links between notes and the note graph.

A link is [[Some title]] inside notes.md. Titles resolve case-insensitively to
the meeting with that exact title (falling back to the meeting id). Encrypted
meetings contribute their node but no outgoing links - the local key may be
absent and the graph must never require decrypting to build.
"""
import json, os, re

LINK_RE = re.compile(r"\[\[([^\[\]|]{1,120})(?:\|([^\[\]]{1,120}))?\]\]")


def extract(text: str):
    """[(target, label)] pairs; label is the display text after an optional |."""
    return [(m.group(1).strip(), (m.group(2) or m.group(1)).strip())
            for m in LINK_RE.finditer(text or "")]


def _norm(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def titles(store_dir: str):
    """{normalized title: mid} for every meeting, metas that fail to read skipped."""
    from iris import store as S
    out = {}
    for mid in S.list_meetings(store_dir):
        try:
            meta = json.load(open(os.path.join(store_dir, mid, "meta.json")))
        except Exception:
            continue
        t = _norm(meta.get("title") or mid)
        out.setdefault(t, mid)
        out.setdefault(_norm(mid), mid)
    return out


def _notes_text(store_dir: str, mid: str):
    """Decrypted notes.md text when readable, else None (locked or absent)."""
    from iris import webui as W
    texts = W.read_meeting_texts(store_dir, mid)
    return (texts or {}).get("notes.md")


def resolve(store_dir: str, target: str):
    """mid for a [[target]], or None when no note has that title."""
    return titles(store_dir).get(_norm(target))


def backlinks(store_dir: str, mid: str):
    """Meetings that link to mid, as [(mid, title)], unreadable metas skipped."""
    from iris import store as S
    mine = _norm(_title_of(store_dir, mid))
    out = []
    for other in S.list_meetings(store_dir):
        if other == mid:
            continue
        txt = _notes_text(store_dir, other)
        if txt is None:
            continue
        for target, _label in extract(txt):
            if _norm(target) == mine or resolve(store_dir, target) == mid:
                out.append((other, _title_of(store_dir, other)))
                break
    return out


def _title_of(store_dir: str, mid: str) -> str:
    try:
        return json.load(open(os.path.join(store_dir, mid, "meta.json"))).get("title", mid)
    except Exception:
        return mid


def graph(store_dir: str):
    """Nodes and edges for the graph view. Edges go from a readable note to the
    note it names; unresolved [[links]] are dropped, locked notes link nowhere."""
    from iris import store as S
    tmap = titles(store_dir)
    nodes, edges, seen = [], [], set()
    for mid in S.list_meetings(store_dir):
        nodes.append({"id": mid, "title": _title_of(store_dir, mid)})
        txt = _notes_text(store_dir, mid)
        if txt is None:
            continue
        for target, _label in extract(txt):
            to = tmap.get(_norm(target))
            if to and to != mid and (mid, to) not in seen:
                seen.add((mid, to))
                edges.append({"from": mid, "to": to})
    return {"nodes": nodes, "edges": edges}
