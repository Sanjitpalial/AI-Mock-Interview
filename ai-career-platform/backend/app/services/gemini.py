import asyncio
import logging
from typing import Any, List, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

logger = logging.getLogger(__name__)

MODEL_FALLBACKS = (
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-flash",
)


def _api_key() -> str:
    key = (settings.GOOGLE_API_KEY or "").strip()
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Add it to backend/.env (Google AI Studio API key)."
        )
    return key


def get_gemini_chat(*, temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    model = (settings.GEMINI_MODEL or "gemini-2.0-flash").strip()
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=_api_key(),
    )


def _models_to_try() -> List[str]:
    primary = (settings.GEMINI_MODEL or "gemini-2.0-flash").strip()
    out = [primary]
    for m in MODEL_FALLBACKS:
        if m not in out:
            out.append(m)
    return out


def invoke_with_model_fallback(messages, *, temperature: float = 0.7):
    """Sync Gemini call with model fallback. Returns (response, model_used)."""
    last_error = None
    for model_name in _models_to_try():
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=_api_key(),
            )
            return llm.invoke(messages), model_name
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini model %s failed: %s", model_name, exc)
    raise ValueError(
        f"All Gemini models failed. Last error: {last_error}. "
        "Check GOOGLE_API_KEY and GEMINI_MODEL=gemini-2.0-flash in .env"
    ) from last_error


async def ainvoke_with_model_fallback(messages, *, temperature: float = 0.7):
    """Async Gemini call with model fallback."""
    last_error = None
    for model_name in _models_to_try():
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=_api_key(),
            )
            return await llm.ainvoke(messages), model_name
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini async model %s failed: %s", model_name, exc)
    raise ValueError(
        f"All Gemini models failed. Last error: {last_error}. "
        "Check GOOGLE_API_KEY and GEMINI_MODEL=gemini-2.0-flash in .env"
    ) from last_error


def invoke_with_model_fallback_thread(messages, *, temperature: float = 0.7):
    """Run sync fallback from async code without blocking the event loop long-term."""
    return invoke_with_model_fallback(messages, temperature=temperature)
