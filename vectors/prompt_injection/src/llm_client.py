"""The model client: local Qwen3 via Ollama by default, optional Gemini for
the attacker. Raises on failure; no silent fallback between providers."""
from __future__ import annotations
import os
import random
import time
from pathlib import Path
import ollama

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass

DEFAULT_MODEL = os.getenv("ADL_LOCAL_MODEL", "qwen3:8b")


def _load_gemini_keys() -> list[str]:
    """GEMINI_API_KEY, then GEMINI_API_KEY_2, _3, ... until one is unset."""
    keys = []
    primary = os.getenv("GEMINI_API_KEY")
    if primary:
        keys.append(primary)
    i = 2
    while (k := os.getenv(f"GEMINI_API_KEY_{i}")):
        keys.append(k)
        i += 1
    return keys


GEMINI_API_KEYS = _load_gemini_keys()
_exhausted_keys: set[int] = set()

# Free-tier gemini-2.5-flash is capped at 10 requests/minute per key. Spacing
# calls at this floor keeps a run under the limit on its own, instead of
# relying on retry/backoff to absorb 429s after the fact.
GEMINI_MIN_INTERVAL = float(os.getenv("ADL_GEMINI_MIN_INTERVAL", "6.5"))
_last_gemini_call = 0.0


def generate_json(system: str, user: str, schema: dict | None = None,
                  model: str | None = None, temperature: float = 0.7,
                  max_tokens: int = 500, repeat_penalty: float = 1.3) -> str:
    """One schema-constrained completion, returned as raw JSON for the caller to parse."""
    model = model or DEFAULT_MODEL
    if model.startswith("gemini"):
        return _gemini_generate(system, user, model, temperature, max_tokens, schema)
    client = ollama.Client()
    resp = client.chat(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        format=schema if schema is not None else "json",
        think=False,
        options={"temperature": temperature, "num_predict": max_tokens,
                "repeat_penalty": repeat_penalty})
    return resp["message"]["content"]


def generate_text(system: str, user: str, model: str | None = None,
                  temperature: float = 0.7, max_tokens: int = 400,
                  repeat_penalty: float = 1.3) -> str:
    """One plain-text completion."""
    model = model or DEFAULT_MODEL
    if model.startswith("gemini"):
        return _gemini_generate(system, user, model, temperature, max_tokens, None)
    client = ollama.Client()
    resp = client.chat(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        think=False,
        options={"temperature": temperature, "num_predict": max_tokens,
                "repeat_penalty": repeat_penalty})
    return resp["message"]["content"]


def _gemini_generate(system: str, user: str, model: str, temperature: float,
                     max_tokens: int, schema: dict | None,
                     max_retries: int = 5) -> str:
    """One Gemini completion, tried across every configured key in turn.

    A 429 marks that key exhausted for the rest of this process and moves to
    the next one immediately - backing off and retrying the same key wastes
    time when the quota is a daily cap, not a transient minute-window limit.
    Non-429 errors still get the backoff retries, since those genuinely can
    be transient. Raises only once every key has failed."""
    if not GEMINI_API_KEYS:
        raise RuntimeError("GEMINI_API_KEY not set - add it to "
                           "vectors/prompt_injection/.env")
    from google import genai
    from google.genai import errors, types

    global _last_gemini_call
    config_kwargs = {"system_instruction": system, "temperature": temperature,
                     "max_output_tokens": max_tokens,
                     "thinking_config": types.ThinkingConfig(thinking_budget=0)}
    if schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_json_schema"] = schema
    config = types.GenerateContentConfig(**config_kwargs)

    last_error: Exception | None = None
    for idx, api_key in enumerate(GEMINI_API_KEYS):
        if idx in _exhausted_keys:
            continue
        client = genai.Client(api_key=api_key)
        delay = 2.0
        for attempt in range(max_retries + 1):
            wait = GEMINI_MIN_INTERVAL - (time.monotonic() - _last_gemini_call)
            if wait > 0:
                time.sleep(wait)
            _last_gemini_call = time.monotonic()
            try:
                resp = client.models.generate_content(model=model, contents=user,
                                                       config=config)
                return resp.text
            except errors.APIError as e:
                last_error = e
                if e.code == 429:
                    _exhausted_keys.add(idx)
                    break
                if attempt == max_retries:
                    break
                wait = min(delay * (2 ** attempt) + random.uniform(0, 1), 60)
                time.sleep(wait)

    raise RuntimeError(
        f"all {len(GEMINI_API_KEYS)} Gemini API key(s) failed - "
        f"last error: {last_error}") from last_error
