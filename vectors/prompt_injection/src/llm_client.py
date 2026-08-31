"""The model client: local Qwen3 via Ollama by default, optional Gemini for
the attacker. Raises on failure; no silent fallback between providers."""
from __future__ import annotations
import os
import random
import sys
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

# Thinking mode spends tokens reasoning before it ever writes the actual
# answer. If num_predict only covers the answer, a long enough thinking pass
# eats the whole budget and the answer comes back empty or cut off mid-JSON -
# the same truncation Gemini hit before its thinking was disabled. This adds
# headroom on top of whatever the caller asked for, so callers can keep
# thinking in max_tokens as "budget for the answer" and not worry about it.
OLLAMA_THINK_BUDGET = 1024


def _ollama_chat(model: str, system: str, user: str, temperature: float,
                 max_tokens: int, repeat_penalty: float,
                 format_: str | dict | None, think: bool = True) -> str:
    """One ollama chat call.

    think=True: fixed headroom isn't a guarantee - a hard enough prompt can
    still spend the whole num_predict budget reasoning and never write an
    answer, coming back with empty content (json.loads on that raises
    "Expecting value" - the same truncation Gemini hit before its thinking
    was disabled). If that happens, retry once with thinking off so
    num_predict goes entirely to the answer instead of failing the caller
    outright.

    think=False: skip thinking entirely - for schema-constrained, mechanical
    completions (e.g. the target agent's tool-call plan) that don't need
    reasoning, where thinking mode was only adding latency and occasionally
    triggering the retry above."""
    client = ollama.Client()

    def _call(think: bool, num_predict: int) -> str:
        kwargs = dict(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            think=think,
            options={"temperature": temperature, "num_predict": num_predict,
                    "repeat_penalty": repeat_penalty})
        if format_ is not None:
            kwargs["format"] = format_
        resp = client.chat(**kwargs)
        return resp["message"]["content"]

    if not think:
        return _call(think=False, num_predict=max_tokens)

    content = _call(think=True, num_predict=max_tokens + OLLAMA_THINK_BUDGET)
    if content.strip():
        return content
    print(f"llm_client: {model} spent its whole budget thinking and returned "
          f"no answer - retrying once with thinking off", file=sys.stderr)
    return _call(think=False, num_predict=max_tokens)


def generate_json(system: str, user: str, schema: dict | None = None,
                  model: str | None = None, temperature: float = 0.7,
                  max_tokens: int = 500, repeat_penalty: float = 1.3,
                  think: bool = True) -> str:
    """One schema-constrained completion, returned as raw JSON for the caller to parse."""
    model = model or DEFAULT_MODEL
    if model.startswith("gemini"):
        return _gemini_generate(system, user, model, temperature, max_tokens, schema)
    return _ollama_chat(model, system, user, temperature, max_tokens, repeat_penalty,
                        schema if schema is not None else "json", think=think)


def generate_text(system: str, user: str, model: str | None = None,
                  temperature: float = 0.7, max_tokens: int = 400,
                  repeat_penalty: float = 1.3, think: bool = True) -> str:
    """One plain-text completion."""
    model = model or DEFAULT_MODEL
    if model.startswith("gemini"):
        return _gemini_generate(system, user, model, temperature, max_tokens, None)
    return _ollama_chat(model, system, user, temperature, max_tokens, repeat_penalty, None, think=think)


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
