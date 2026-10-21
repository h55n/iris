"""Notes backends. Default: local Ollama/Gemma (runs on user's machine, no cloud).
Fallback: Ultramarine (hosted, used in dev/sandbox where no GPU/llama exists).
Every backend returns notes JSON: summary, decisions[], action_items[] - each
decision/action item MUST carry `evidence`: a verbatim quote from the transcript."""
import json, os, urllib.request

PROMPT = """You are the notes engine for a private meeting recorder. Given a transcript with [MM:SS] timestamps, produce JSON only:
{"summary": "2-3 sentences", "decisions": [{"text": "...", "evidence": "verbatim transcript quote", "at": "MM:SS"}], "action_items": [{"text": "...", "owner": "name or null", "evidence": "verbatim transcript quote", "at": "MM:SS"}]}
Rules: evidence must be copied word-for-word from the transcript. If nothing was decided, decisions=[]. If no tasks, action_items=[]. Never invent names, dates or tasks.

TRANSCRIPT:
"""

def _chat(url, payload, headers=None, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def _parse_notes(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw)

class OllamaBackend:
    name = "ollama"
    def __init__(self, model=None, base="http://127.0.0.1:11434"):
        self.model = model or os.environ.get("IRIS_OLLAMA_MODEL", "gemma3:4b")
        self.base = base
    def notes(self, transcript_md: str) -> dict:
        try:
            r = _chat(f"{self.base}/api/generate",
                      {"model": self.model, "prompt": PROMPT + transcript_md,
                       "stream": False, "format": "json"})
        except Exception as e:
            raise RuntimeError(
                f"local notes backend unreachable ({self.base}) - is ollama running? "
                f"Fix: `ollama serve` + `ollama pull {self.model}`, "
                f"or use --backend ultramarine. ({type(e).__name__})") from e
        return _parse_notes(r["response"])

class UltramarineBackend:
    name = "ultramarine"
    def __init__(self, key=None):
        self.key = key or os.environ.get("IRIS_ULTRAMARINE_KEY", "")
    def notes(self, transcript_md: str) -> dict:
        if not self.key:
            raise RuntimeError("no Ultramarine key - set IRIS_ULTRAMARINE_KEY, "
                               "or use the default local backend (ollama)")
        r = _chat("https://api.paperinstruments.com/v1/chat/completions",
                  {"model": "ultramarine-1-flash",
                   "messages": [{"role": "user", "content": PROMPT + transcript_md}]},
                  headers={"Authorization": f"Bearer {self.key}"})
        _log_usage(r)
        return _parse_notes(r["choices"][0]["message"]["content"])

USAGE_LOG = os.environ.get("IRIS_USAGE_LOG", os.path.expanduser("~/.iris/hosted-usage.jsonl"))

def _log_usage(response: dict):
    """Track hosted-backend token usage locally, so the real spend is visible
    (the DEV post cites actual spend, not a guess)."""
    u = (response or {}).get("usage") or {}
    rec = {"ts": __import__("time").time(), "backend": "ultramarine",
           "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")}
    try:
        os.makedirs(os.path.dirname(USAGE_LOG), exist_ok=True)
        with open(USAGE_LOG, "a") as f:
            f.write(__import__("json").dumps(rec) + "\n")
    except Exception:
        pass

def get_backend(name: str):
    return {"ollama": OllamaBackend, "ultramarine": UltramarineBackend}[name]()
