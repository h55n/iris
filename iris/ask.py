"""Ask across your meetings. Retrieval only, no model: every answer is a
transcript line quoted with its meeting and timestamp, so nothing can be
invented. Scoring is plain term overlap with a stopword list."""
import re

STOP = set("a an and are as at be by did do does for from had has have how i in is it its of on or "
           "our so that the their then there they this to was we were what when where which who why "
           "will with you your about said say talk talked".split())

def terms(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w\u0900-\u097F']+", text.lower()) if w not in STOP and len(w) > 1]
