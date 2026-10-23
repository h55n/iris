import json, os, tempfile
import pytest
from iris import links as LK, store as S


def _store():
    d = tempfile.mkdtemp()
    a = S.new_meeting(d, "Weekly sync")
    b = S.new_meeting(d, "Roadmap")
    c = S.new_meeting(d, "Orphan")
    S.write_text(d, a, "notes.md", "# Weekly sync\n- discussed [[Roadmap]] and [[Missing note]]\n- alias [[roadmap|the plan]]")
    S.write_text(d, b, "notes.md", "# Roadmap\n- back to [[Weekly sync]]")
    S.write_text(d, c, "notes.md", "# Orphan\n- no links here")
    return d, a, b, c


def test_extract_links_and_aliases():
    pairs = LK.extract("see [[A]], [[B|bee]], not [[too " + "x" * 200 + "long]]")
    assert ("A", "A") in pairs and ("B", "bee") in pairs
    assert all(len(t) <= 120 for t, _ in pairs)


def test_resolve_is_case_insensitive():
    d, a, b, c = _store()
    assert LK.resolve(d, "roadmap") == b and LK.resolve(d, "ROADMAP") == b
    assert LK.resolve(d, "Missing note") is None


def test_backlinks():
    d, a, b, c = _store()
    assert [m for m, _ in LK.backlinks(d, b)] == [a]      # Roadmap linked from Weekly sync
    assert [m for m, _ in LK.backlinks(d, a)] == [b]
    assert LK.backlinks(d, c) == []


def test_graph_nodes_edges_no_self_or_dups():
    d, a, b, c = _store()
    g = LK.graph(d)
    assert len(g["nodes"]) == 3
    edge_set = {(e["from"], e["to"]) for e in g["edges"]}
    assert edge_set == {(a, b), (b, a)}                    # alias link dedupes into one edge
    assert all(f != t for f, t in edge_set)


def test_encrypted_meeting_is_a_node_but_has_no_edges():
    d, a, b, c = _store()
    S.write_text(d, c, "notes.md", "# Orphan\n- secretly links to [[Roadmap]]")
    import iris.crypto as CR, shutil
    shutil.rmtree(d + "/" + c); os.makedirs(d + "/" + c)
    meta = {"title": "Orphan", "created": 1}
    json.dump(meta, open(d + "/" + c + "/meta.json", "w"))
    open(d + "/" + c + "/notes.md.age", "w").write("AGE-ENCRYPTED-FAKE")  # not decryptable
    json.dump({**meta, "encrypted": True}, open(d + "/" + c + "/meta.json", "w"))
    g = LK.graph(d)
    assert any(n["id"] == c for n in g["nodes"])
    assert not any(e["from"] == c for e in g["edges"])


def test_recap_extract_and_summarize():
    from iris import recap as RC
    ds, acs = RC.extract_from_notes("# M\n## Decisions\n- ship Friday\n\n## Action items\n- [ ] call Priya\n- [x] book room\n")
    assert ds == ["ship Friday"] and acs == [("call Priya", False), ("book room", True)]
    now = 1_000_000_000.0
    r = RC.summarize([("Old", now - 9 * 86400, "## Decisions\n- old call", 0),
                      ("New", now - 3600, "## Action items\n- [ ] fresh task", 2)], now=now)
    assert [m["title"] for m in r["meetings"]] == ["New"]
    assert r["actions"] == [{"text": "fresh task", "done": False, "source": "New"}]
    assert r["link_count"] == 2 and r["decisions"] == []
