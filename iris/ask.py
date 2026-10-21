"""Ask across your meetings. Retrieval only, no model: every answer is a
transcript line quoted with its meeting and timestamp, so nothing can be
invented. Scoring is plain term overlap with a stopword list."""
import re

STOP = set("a an and are as at be by did do does for from had has have how i in is it its of on or "
           "our so that the their then there they this to was we were what when where which who why "
           "will with you your about said say talk talked".split())

def terms(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w\u0900-\u097F']+", text.lower()) if w not in STOP and len(w) > 1]


LINE = re.compile(r"^\[(\d\d:\d\d(?::\d\d)?)\] (.*)$")

def score_line(q_terms: list[str], line: str) -> float:
    """Share of distinct question terms found in the line (0..1)."""
    if not q_terms:
        return 0.0
    have = set(terms(line))
    want = set(q_terms)
    return len(want & have) / len(want)

def ask(store_dir: str, question: str, key_path: str | None = None,
        limit: int = 5, min_score: float = 0.34) -> list[dict]:
    """Best-matching transcript lines across all readable meetings, each with
    its meeting id, title, timestamp and the exact quoted line."""
    import json, os
    from iris import export as E, store as S
    q = terms(question)
    hits = []
    for mid in S.list_meetings(store_dir):
        try:
            texts = E._get_texts(store_dir, mid, key_path)
            title = json.load(open(os.path.join(store_dir, mid, "meta.json"))).get("title", mid)
        except Exception:
            continue  # locked or unreadable meeting
        for line in texts.get("transcript.md", "").splitlines():
            m = LINE.match(line.strip())
            if not m:
                continue
            s = score_line(q, m.group(2))
            if s >= min_score:
                quote = re.sub(r"(^[^:]+: )<[a-z]{2,8}> ", r"\1", m.group(2))  # drop language tags
                hits.append({"meeting": mid, "title": title, "at": m.group(1),
                             "quote": quote, "score": round(s, 2)})
    hits.sort(key=lambda h: (-h["score"], h["meeting"], h["at"]))
    return hits[:limit]
