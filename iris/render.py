"""Shared notes.md renderer."""

def render_notes(mid, notes, segs):
    lines = [f"# Notes: {mid}", "", "## Summary", notes.get("summary", ""), "", "## Decisions"]
    for d in notes.get("decisions", []):
        lines.append(f"- {d.get('text', '(untitled)')}  ")
        lines.append(f"  > \"{d.get('evidence', '')}\" [{d.get('at', '?')}]")
    if notes.get("unverified_decisions"):
        lines += ["", "### Unverified (model claimed, transcript disagrees - kept for honesty)"]
        for d in notes["unverified_decisions"]:
            lines.append(f"- {d['text']} ({d['unverified_reason']})")
    lines += ["", "## Action items"]
    for a in notes.get("action_items", []):
        owner = f" ({a['owner']})" if a.get("owner") else ""
        lines.append(f"- [ ] {a.get('text', '(untitled)')}{owner}  ")
        lines.append(f"  > \"{a.get('evidence', '')}\" [{a.get('at', '?')}]")
    if notes.get("unverified_action_items"):
        lines += ["", "### Unverified (model claimed, transcript disagrees - kept for honesty)"]
        for a in notes["unverified_action_items"]:
            lines.append(f"- {a['text']} ({a['unverified_reason']})")
    i = notes.get("integrity", {})
    lines += ["", f"_integrity: {i.get('passed', 0)}/{i.get('checked', 0)} claims verified against transcript_"]
    return "\n".join(lines)

