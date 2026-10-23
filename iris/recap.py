"""On-demand recap of recent notes. Extraction only: nothing here confirms what
is actually done or outstanding - it surfaces what the notes say, so the reader
can judge. Encrypted/locked notes are excluded by the callers (no plaintext)."""
import re, time

SEC_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$")


def extract_from_notes(notes_md: str):
    """(decisions, action_items) found in one notes document.
    action_items: [(text, done)] from checkboxes or bullets under action headings."""
    decisions, actions, sec = [], [], ""
    for line in (notes_md or "").splitlines():
        m = SEC_RE.match(line.strip())
        if m:
            sec = m.group(1).lower()
            continue
        t = line.strip()
        if not (t.startswith("- ") or t.startswith("* ")):
            continue
        body = t[2:]
        if re.match(r"^\[[ xX]\] ", body):
            actions.append((body[4:].strip(), body[1] != " "))
        elif "decision" in sec or "decided" in sec:
            decisions.append(body)
        elif "action" in sec or "to do" in sec or "to-do" in sec:
            actions.append((body, False))
    return decisions, actions


def summarize(entries, days: int = 7, now: float = None):
    """entries: [(title, created_ts, notes_md, link_count)]. Returns a recap dict
    covering the newest `days` days."""
    now = now if now is not None else time.time()
    cutoff = now - days * 86400
    recent = [e for e in entries if (e[1] or 0) >= cutoff]
    meetings, decisions, actions, links = [], [], [], 0
    for title, created, notes_md, link_count in sorted(recent, key=lambda e: e[1] or 0):
        meetings.append({"title": title, "created": created})
        ds, acs = extract_from_notes(notes_md)
        decisions += [{"text": d, "source": title} for d in ds]
        actions += [{"text": a, "done": done, "source": title} for a, done in acs]
        links += link_count
    return {"days": days, "meetings": meetings, "decisions": decisions,
            "actions": actions, "link_count": links}
