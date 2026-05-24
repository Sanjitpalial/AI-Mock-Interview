from langchain_core.messages import HumanMessage, SystemMessage
import json
import re
import logging

from app.services.gemini import ainvoke_with_model_fallback
from app.agents.llm_utils import message_text

logger = logging.getLogger(__name__)

EVAL_PROMPT = """
You are an expert interviewer. Score the candidate answer briefly.

Return ONLY valid JSON with these keys (numbers 0.0 to 1.0):
technical_accuracy, communication, confidence, grammar, sentiment,
feedback (array of 3 specific strings: one strength, one gap, one actionable tip),
correct_answer_hint (one short sentence).

sentiment = emotional tone and positivity of the answer (not grammar).

No markdown. No extra keys.
"""


def _normalize_feedback(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        return [raw]
    return [str(raw)]


def _parse_json_scores(content: str):
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _fallback_scores(reason: str = "") -> dict:
    hint = "Could not reach the AI evaluator; default scores applied."
    if reason:
        hint = f"{hint} ({reason[:120]})"
    return {
        "technical_accuracy": 0.5,
        "communication": 0.5,
        "confidence": 0.5,
        "grammar": 0.5,
        "feedback": [
            "Your answer was saved.",
            "Check GOOGLE_API_KEY in backend/.env if scores look generic.",
        ],
        "correct_answer_hint": hint,
        "similarity_score": 0.0,
        "sentiment": 0.5,
    }


async def evaluate_answer(
    question: str,
    answer: str,
    expected: str,
    speech_metrics: dict | None = None,
) -> dict:
    q = (question or "")[:800]
    a = (answer or "")[:2500]
    exp = (expected or "")[:400]

    human = f"Question: {q}\n\nAnswer: {a}\n\nThemes: {exp or 'general interview'}"
    if speech_metrics and speech_metrics.get("answer_mode") == "voice":
        human += (
            f"\n\nVoice: {speech_metrics.get('duration_sec')}s, "
            f"{speech_metrics.get('words_per_minute')} WPM, "
            f"{speech_metrics.get('pause_count')} pauses, "
            f"{speech_metrics.get('filler_count')} fillers."
        )

    messages = [
        SystemMessage(content=EVAL_PROMPT),
        HumanMessage(content=human),
    ]

    try:
        response, _ = await ainvoke_with_model_fallback(messages, temperature=0)
        content = message_text(response)
        scores = _parse_json_scores(content)
    except Exception as exc:
        logger.exception("Gemini evaluation failed, using fallback scores")
        scores = _fallback_scores(str(exc))

    if not scores:
        scores = _fallback_scores("empty model response")

    scores["feedback"] = _normalize_feedback(scores.get("feedback"))
    scores["similarity_score"] = float(scores.get("similarity_score", 0.0))

    for key in ("technical_accuracy", "communication", "confidence", "grammar", "sentiment"):
        try:
            scores[key] = float(scores.get(key, 0.5))
        except (TypeError, ValueError):
            scores[key] = 0.5

    if speech_metrics and speech_metrics.get("answer_mode") == "voice":
        fluency = float(speech_metrics.get("fluency_score") or 0.5)
        vocab = float(speech_metrics.get("vocabulary_score") or 0.5)
        scores["communication"] = min(
            1.0,
            scores["communication"] * 0.65 + fluency * 0.2 + vocab * 0.15,
        )
        scores["confidence"] = min(1.0, scores["confidence"] * 0.7 + fluency * 0.3)

    return scores
