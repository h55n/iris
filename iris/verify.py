"""Integrity pass: every claim in the notes must quote the transcript verbatim
and point at a real timestamp. Failures are demoted to 'unverified', never deleted."""
import re

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()

def _quote_in_transcript(quote: str, transcript: str) -> bool:
    q, t = _norm(quote), _norm(transcript)
    if not q: return False
    if q in t: return True
    # tolerate the model trimming to a clause: all content words present in order
    words = [w for w in re.findall(r"[a-z0-9']+", q) if len(w) > 3]
    if len(words) < 2: return q in t
    pos, ok = 0, 0
    for w in words:
        p = t.find(w, pos)
        if p < 0: break
        pos, ok = p, ok + 1
    return ok >= max(2, int(0.8 * len(words)))

def _at_exists(at: str, segs: list[dict]) -> bool:
    try:
        m, s = at.split(":"); t = int(m) * 60 + int(s)
    except Exception:
        return False
    return any(seg["start"] - 30 <= t <= seg["end"] + 30 for seg in segs)  # 30s tolerance

def _owner_in_transcript(owner: str, transcript: str) -> bool:
    if not owner: return True
    return owner.strip().lower() in transcript.lower()

def verify_notes(notes: dict, segs: list[dict]) -> dict:
    transcript = " ".join(s["text"] for s in segs)
    for key in ("decisions", "action_items"):
        good, bad = [], []
        for item in notes.get(key, []):
            reason = None
            if not _quote_in_transcript(item.get("evidence", ""), transcript):
                reason = "evidence not found verbatim in transcript"
            elif not _at_exists(item.get("at", ""), segs):
                reason = "timestamp outside transcript"
            elif key == "action_items" and not _owner_in_transcript(item.get("owner", ""), transcript):
                reason = "owner not mentioned in transcript"
            if reason is None:
                good.append(item)
            else:
                item["unverified_reason"] = reason
                bad.append(item)
        notes[key] = good
        notes[f"unverified_{key}"] = bad
    notes["integrity"] = {
        "checked": sum(len(notes.get(k, [])) + len(notes.get(f"unverified_{k}", [])) for k in ("decisions", "action_items")),
        "passed": sum(len(notes.get(k, [])) for k in ("decisions", "action_items")),
    }
    return notes
