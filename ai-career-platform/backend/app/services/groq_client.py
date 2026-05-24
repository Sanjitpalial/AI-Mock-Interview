"""Shared Groq client for Study Assistant."""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_client = None

GROQ_MODEL_FALLBACKS = (
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
)


def require_groq_key() -> str:
    key = (settings.GROQ_API_KEY or "").strip()
    if not key or key.startswith("your-") or key == "your-groq-api-key-here":
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to backend/.env (https://console.groq.com/keys)."
        )
    return key


def _friendly_groq_error(exc: Exception) -> str:
    msg = str(exc).strip()
    lower = msg.lower()
    if "invalid_api_key" in lower or "invalid api key" in lower:
        return (
            "Groq rejected your API key (invalid or revoked). "
            "Create a new key at https://console.groq.com/keys and set GROQ_API_KEY in backend/.env, then restart the server."
        )
    if "rate" in lower or "quota" in lower:
        return f"Groq rate limit: {msg}"
    return msg


def verify_groq_connection() -> None:
    """Single-model API check — raises ValueError if the key does not work."""
    global _client
    key = require_groq_key()
    if _client is None:
        from groq import Groq

        _client = Groq(api_key=key)
    model_name = (settings.GROQ_MODEL or "llama-3.1-8b-instant").strip()
    try:
        response = _client.chat.completions.create(
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            model=model_name,
            temperature=0,
            max_tokens=8,
        )
        if not (response.choices[0].message.content or "").strip():
            raise ValueError(f"Groq model {model_name} returned empty content")
    except Exception as exc:
        raise ValueError(_friendly_groq_error(exc)) from exc


def _models_to_try() -> list[str]:
    primary = (settings.GROQ_MODEL or "llama-3.1-8b-instant").strip()
    out = [primary]
    for m in GROQ_MODEL_FALLBACKS:
        if m not in out:
            out.append(m)
    return out


def groq_chat(prompt: str, *, temperature: float = 0.3) -> str:
    global _client
    key = require_groq_key()
    if _client is None:
        from groq import Groq

        _client = Groq(api_key=key)

    last_error: Exception | None = None
    for model_name in _models_to_try():
        try:
            response = _client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                temperature=temperature,
                max_tokens=4096,
            )
            content = (response.choices[0].message.content or "").strip()
            if content:
                return content
            last_error = ValueError(f"Groq model {model_name} returned empty content")
        except Exception as exc:
            last_error = exc
            logger.warning("Groq model %s failed: %s", model_name, exc)

    friendly = _friendly_groq_error(last_error) if last_error else "Unknown Groq error"
    raise ValueError(
        f"Groq request failed: {friendly} "
        "(set GROQ_MODEL=llama-3.1-8b-instant in backend/.env if needed)"
    ) from last_error
