"""Hinglish detection from text alone (no model, no network).

Whisper tags a segment 'hi' or 'en', but people speak Hindi in Roman
letters and mix both in one sentence. A segment is:
  hi        mostly Devanagari
  hinglish  Roman letters with Hindi function words, or Devanagari mixed
            with real English words
  en        everything else
The marker list is common Hindi function and filler words; each is rare
as an English word, so two hits (or one in a short line) is a strong signal."""
import re

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN_WORD = re.compile(r"[A-Za-z']+")

HI_ROMAN = set("""hai hain tha thi the ho hoga hogi hoon kya kyun kyu kaise kab kahan kaun kitna kitne
nahi nahin nhi mat haan han ji accha acha theek thik bas abhi aaj kal ab phir toh to bhi
aur ya lekin par magar mera meri mere tera teri tere hamara hamari hum tum aap yeh ye woh wo
isko usko isme usme isse usse karna karo kar kiya kare karenge karna raha rahi rahe gaya gayi gaye
chahiye chahta chahte sakta sakte sakti lagta lagte bahut jyada zyada kam sab kuch koi kyunki
matlab samajh dekho dekhna bolo bol bata batao suno sun chalo chal milte milna baat kaam
yaar bhai didi sir ke ki ka ko se mein me pe liye wala wali""".split())

# English words that are also Roman-Hindi words; never count these as Hindi evidence
AMBIGUOUS = {"to", "the", "me", "ho", "the", "par", "ab", "kam", "bas", "ya", "sir", "ke", "ka", "ki", "ko", "se", "pe", "mat", "tha", "thi", "ji", "do", "bol", "sun", "chal", "mera"}

def classify(text: str) -> str:
    letters = len(re.findall(r"[A-Za-z\u0900-\u097F]", text))
    if letters == 0:
        return "en"
    deva = len(DEVANAGARI.findall(text))
    words = [w.lower() for w in LATIN_WORD.findall(text)]
    if deva / letters > 0.5:
        # Hindi script, but with a real run of English words it is mixed
        return "hinglish" if len(words) >= 3 and len(words) / max(1, len(text.split())) > 0.3 else "hi"
    strong = [w for w in words if w in HI_ROMAN and w not in AMBIGUOUS]
    if deva:
        return "hinglish"
    need = 1 if len(words) <= 4 else 2
    return "hinglish" if len(strong) >= need else "en"
