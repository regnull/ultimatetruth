"""Ask each model the question and write answers to site/answers.json.

Keys are read from the environment: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, XAI_API_KEY,
OPENROUTER_API_KEY.
Usage: python3 scripts/ask.py [model-id ... | all]   (no args = only models without an answer)
"""
import json, os, sys, datetime, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

QUESTION = (
    "Considering everything humanity knows from history, philosophy, religion, and science, "
    "what is the ultimate truth? Don't survey perspectives, break the question into parts, or "
    "explain your reasoning steps. Don't tell me it depends on definitions or that there's no "
    "single answer. Commit to one answer, the one you find most defensible, and state it plainly "
    "in a few sentences, as if you had to stand behind it."
)

# (id, display name, maker, provider, open_weights)
MODELS = [
    ("gpt-6.1-sol", "GPT-6.1 Sol", "OpenAI", "openai", False),
    ("gpt-6-astra", "GPT-6 Astra", "OpenAI", "openai", False),
    ("gpt-5.5-pro", "GPT-5.5 Pro", "OpenAI", "openai", False),
    ("claude-fable-5-1", "Claude Fable 5.1", "Anthropic", "anthropic", False),
    ("claude-opus-5-5", "Claude Opus 5.5", "Anthropic", "anthropic", False),
    ("claude-sonnet-5-5", "Claude Sonnet 5.5", "Anthropic", "anthropic", False),
    ("gemini-4-argon", "Gemini 4 Argon", "Google", "google", False),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro", "Google", "google", False),
    ("grok-4.7", "Grok 4.7", "xAI", "xai", False),
    ("gemma-4-31b-it", "Gemma 4 31B", "Google", "google", True),
    ("gemma-4-26b-a4b-it", "Gemma 4 26B A4B", "Google", "google", True),
    ("deepseek/deepseek-v4-pro-0813", "DeepSeek V4 Pro", "DeepSeek", "openrouter", True),
    ("moonshotai/kimi-k3", "Kimi K3", "Moonshot AI", "openrouter", True),
    ("qwen/qwen3.8-2.4t-a95b", "Qwen3.8 2.4T", "Alibaba", "openrouter", True),
    ("z-ai/glm-5.3", "GLM-5.3", "Z.ai", "openrouter", True),
    ("minimax/minimax-m3", "MiniMax M3", "MiniMax", "openrouter", True),
    ("nvidia/nemotron-3-ultra-550b-a55b", "Nemotron 3 Ultra", "NVIDIA", "openrouter", True),
    ("openai/gpt-oss-120b", "gpt-oss-120b", "OpenAI", "openrouter", True),
]

OUT = os.path.join(os.path.dirname(__file__), "..", "site", "answers.json")


def post(url, headers, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=3600) as r:
        return json.load(r)


def post_sse(url, headers, body):
    """Stream an Anthropic Messages request and return the concatenated text."""
    req = urllib.request.Request(url, json.dumps({**body, "stream": True}).encode(),
                                 {"Content-Type": "application/json", **headers})
    text = []
    with urllib.request.urlopen(req, timeout=3600) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:])
            if ev["type"] == "content_block_delta" and ev["delta"]["type"] == "text_delta":
                text.append(ev["delta"]["text"])
            elif ev["type"] == "error":
                raise RuntimeError(ev["error"])
    return "".join(text)


# Highest reasoning setting first; a 400 falls through to the next one.
EFFORTS = {
    "openai": ["xhigh", "high"],
    "anthropic": ["max"],
    "google": ["high", None],
    "xai": ["high", None],
    "openrouter": ["xhigh", "high"],
}


def ask(model, provider, effort):
    if provider == "openai":
        d = post("https://api.openai.com/v1/responses",
                 {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                 {"model": model, "input": QUESTION, "reasoning": {"effort": effort}})
        return "".join(c["text"] for o in d["output"] if o["type"] == "message" for c in o["content"] if c["type"] == "output_text")
    if provider == "anthropic":
        return post_sse("https://api.anthropic.com/v1/messages",
                        {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                        {"model": model, "max_tokens": 64000, "thinking": {"type": "adaptive"},
                         "output_config": {"effort": effort},
                         "messages": [{"role": "user", "content": QUESTION}]})
    if provider == "google":
        body = {"contents": [{"role": "user", "parts": [{"text": QUESTION}]}]}
        if effort:
            body["generationConfig"] = {"thinkingConfig": {"thinkingLevel": effort}}
        d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                 {"x-goog-api-key": os.environ["GOOGLE_API_KEY"]}, body)
        return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
    if provider == "xai":
        body = {"model": model, "messages": [{"role": "user", "content": QUESTION}]}
        if effort:
            body["reasoning_effort"] = effort
        d = post("https://api.x.ai/v1/chat/completions",
                 {"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"}, body)
        return d["choices"][0]["message"]["content"]
    if provider == "openrouter":
        d = post("https://openrouter.ai/api/v1/chat/completions",
                 {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                 {"model": model, "messages": [{"role": "user", "content": QUESTION}],
                  "reasoning": {"effort": effort}})
        return d["choices"][0]["message"]["content"]
    raise ValueError(provider)


def run(m):
    mid, name, maker, provider, open_w = m
    for effort in EFFORTS[provider]:
        try:
            text = ask(mid, provider, effort).strip()
            print(f"ok   {mid} (effort={effort})", file=sys.stderr)
            return {"id": mid, "name": name, "maker": maker, "open_weights": open_w, "effort": effort,
                    "answer": text, "date": datetime.date.today().isoformat()}
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            print(f"FAIL {mid} (effort={effort}): {e} {body}", file=sys.stderr)
            if e.code != 400:
                return
        except Exception as e:
            print(f"FAIL {mid} (effort={effort}): {e}", file=sys.stderr)
            return


def main():
    wanted = set(sys.argv[1:])
    if wanted == {"all"}:
        wanted = {m[0] for m in MODELS}
    existing = {}
    if os.path.exists(OUT):
        existing = {a["id"]: a for a in json.load(open(OUT))["answers"]}
    todo = [m for m in MODELS if (m[0] in wanted) if wanted] if wanted else [m for m in MODELS if m[0] not in existing]
    with ThreadPoolExecutor(len(todo) or 1) as ex:
        for r in ex.map(run, todo):
            if r:
                existing[r["id"]] = r
    order = [m[0] for m in MODELS]
    answers = sorted(existing.values(), key=lambda a: order.index(a["id"]) if a["id"] in order else 99)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"question": QUESTION, "answers": answers}, open(OUT, "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
