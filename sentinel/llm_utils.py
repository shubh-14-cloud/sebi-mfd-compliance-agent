"""
Shared Gemini helpers — one client, JSON-mode generation with retry.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parents[1] / ".env", override=True)

MODEL = "gemini-2.5-flash"
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


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def generate_json(
    system: str,
    prompt: str,
    validate: Optional[Callable[[Any], Any]] = None,
    retries: int = 2,
) -> Any:
    """
    Call Gemini in JSON mode (response_mime_type=application/json), parse the
    result and optionally validate it (e.g. a Pydantic model's model_validate).
    Retries on API, parse or validation errors; raises the last error if all fail.
    """
    last_exc: Exception = RuntimeError("generate_json: no attempts made")
    for _ in range(retries + 1):
        try:
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
    raise last_exc
