"""
Shared Gemini helpers — one client, JSON-mode generation with retry.
"""
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parents[1] / ".env", override=True)

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
# Free-tier keys allow ~5 requests/minute; set GEMINI_RPM higher if your plan does.
_RPM = max(1.0, float(os.environ.get("GEMINI_RPM", "5")))
_MIN_INTERVAL = 60.0 / _RPM
_rate_lock = threading.Lock()
_next_slot = 0.0
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Lazily create the client so importing the package never needs an API key."""
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set (copy .env.example to .env)")
        _client = genai.Client(api_key=key)
    return _client


def _wait_for_slot() -> None:
    """Space API calls at least _MIN_INTERVAL apart (thread-safe), staying under the RPM quota."""
    global _next_slot
    with _rate_lock:
        now = time.monotonic()
        start = max(now, _next_slot)
        _next_slot = start + _MIN_INTERVAL
    if start > now:
        time.sleep(start - now)


def _retry_delay(exc: Exception, attempt: int) -> float:
    """Honour the server's 'retry in Ns' hint if present, else exponential backoff."""
    m = re.search(r"retry in ([\d.]+)s|retryDelay'?\"?: ?'?\"?(\d+)s", str(exc))
    if m:
        return float(m.group(1) or m.group(2)) + 1.0
    return float(2 ** (attempt + 1))


_TRANSIENT_CODES = {429, 500, 503, 504}


def _is_transient(exc: Exception) -> bool:
    """Rate limit / overload / server errors are worth waiting out; bad keys are not."""
    return getattr(exc, "code", None) in _TRANSIENT_CODES


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def generate_json(
    system: str,
    prompt: str,
    validate: Optional[Callable[[Any], Any]] = None,
    retries: int = 4,
) -> Any:
    """
    Call Gemini in JSON mode (response_mime_type=application/json), parse the
    result and optionally validate it (e.g. a Pydantic model's model_validate).
    Retries on API, parse or validation errors; transient API errors (429/5xx) back
    wait for the delay Google suggests (else 2s, 4s, 8s, ...). Raises the last error if all attempts fail.
    """
    last_exc: Exception = RuntimeError("generate_json: no attempts made")
    for attempt in range(retries + 1):
        try:
            _wait_for_slot()
            response = get_client().models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(_strip_fences(response.text))
            return validate(data) if validate else data
        except Exception as exc:  # API error, bad JSON or failed validation
            last_exc = exc
            if attempt < retries and _is_transient(exc):
                time.sleep(_retry_delay(exc, attempt))
    raise last_exc
