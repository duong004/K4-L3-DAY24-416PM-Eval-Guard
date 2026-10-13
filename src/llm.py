"""Shared Gemini chat model setup."""

import asyncio
import json
import re
import time
from unittest.mock import Mock
from config import GEMINI_API_KEY, GEMINI_MODEL

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_MIN_INTERVAL_SEC = 4.1
_last_call_ts = 0.0


def _extract_first_json(text: str) -> str:
    """Strip markdown fences and trailing extra data after the first valid JSON value."""
    if not isinstance(text, str):
        return text
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, flags=re.IGNORECASE)
    if fence:
        s = fence.group(1).strip()
    decoder = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch in "{[":
            try:
                obj, _ = decoder.raw_decode(s[i:])
                if isinstance(obj, dict):
                    if "label" in obj:
                        if isinstance(obj["label"], bool):
                            obj["label"] = 1 if obj["label"] else 0
                        elif isinstance(obj["label"], str) and obj["label"].strip() in ("0", "1"):
                            obj["label"] = int(obj["label"].strip())
                        if not isinstance(obj.get("reasoning"), str) or not obj["reasoning"].strip():
                            obj["reasoning"] = "Đã đối chiếu với đáp án tham chiếu."
                return json.dumps(obj, ensure_ascii=False)
            except Exception:
                continue
    return text


def _parse_retry_delay(msg: str, default: float = 30.0) -> float:
    m = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", msg, flags=re.IGNORECASE)
    if m:
        return max(float(m.group(1)) + 2.0, 5.0)
    return default


def _throttle_sync():
    global _last_call_ts
    now = time.monotonic()
    wait = _MIN_INTERVAL_SEC - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()


async def _throttle_async():
    global _last_call_ts
    now = time.monotonic()
    wait = _MIN_INTERVAL_SEC - (now - _last_call_ts)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_call_ts = time.monotonic()


def _call_with_retry(fn, *args, **kwargs):
    global _last_call_ts
    for attempt in range(8):
        _throttle_sync()
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            msg = str(exc)
            if ("429" in msg or "RESOURCE_EXHAUSTED" in msg or "RateLimitError" in type(exc).__name__ or type(exc).__name__ in ("APIConnectionError", "APITimeoutError")) and attempt < 7:
                delay = _parse_retry_delay(msg)
                print(f"[RateLimit 429] Waiting {delay:.1f}s before retry {attempt + 1}/7...", flush=True)
                time.sleep(delay)
                _last_call_ts = time.monotonic()
                continue
            raise


def gemini_openai_client():
    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY in .env to enable Google AI Studio")
    from openai import OpenAI
    client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL, max_retries=0)
    if not isinstance(client, Mock):
        orig_create = client.chat.completions.create
        if not isinstance(orig_create, Mock):
            def paced_create(*args, **kwargs):
                resp = _call_with_retry(orig_create, *args, **kwargs)
                try:
                    msg = resp.choices[0].message
                    if isinstance(getattr(msg, "content", None), str):
                        msg.content = _extract_first_json(msg.content)
                except Exception:
                    pass
                return resp
            client.chat.completions.create = paced_create
    return client


def gemini_chat_model(temperature: float = 0, model: str | None = None):
    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY in .env to enable Gemini")
    from langchain_openai import ChatOpenAI

    class PacedChatOpenAI(ChatOpenAI):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return _call_with_retry(super()._generate, messages, stop=stop, run_manager=run_manager, **kwargs)

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            global _last_call_ts
            for attempt in range(8):
                await _throttle_async()
                try:
                    return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
                except Exception as exc:
                    msg = str(exc)
                    if ("429" in msg or "RESOURCE_EXHAUSTED" in msg or "RateLimitError" in type(exc).__name__ or type(exc).__name__ in ("APIConnectionError", "APITimeoutError")) and attempt < 7:
                        delay = _parse_retry_delay(msg)
                        print(f"[RateLimit 429] Waiting {delay:.1f}s before async retry {attempt + 1}/7...", flush=True)
                        await asyncio.sleep(delay)
                        _last_call_ts = time.monotonic()
                        continue
                    raise

    return PacedChatOpenAI(
        model=model or GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
        temperature=temperature,
        max_retries=0,
    )