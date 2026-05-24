"""Batch interview analysis after all questions are answered."""

from __future__ import annotations

import json
import logging
from statistics import mean
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.agents.evaluation_agent import evaluate_answer
from app.agents.llm_utils import message_text
from app.models.interview import Answer, Interview, Question
from app.services.gemini import ainvoke_with_model_fallback
from app.services.speech_service import analyze_sentiment_local

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """
You are a senior interview coach. Given scored Q&A from one mock interview, write concise coaching feedback.

Return ONLY valid JSON:
{
  "overall_feedback": ["2-4 complete sentences on overall performance"],
  "strengths": ["2-3 short bullets"],
  "improvements": ["2-3 short bullets"],
  "speech_tips": ["1-2 tips if voice answers were used, else empty array"],
  "sentiment_summary": "one sentence on tone and confidence"
}

No markdown.
"""


def _overall_percent(scores: dict) -> int:
    keys = ("technical_accuracy", "communication", "confidence", "grammar", "sentiment")
    vals = [float(scores.get(k) or 0.5) for k in keys]
    return round(sum(vals) / len(vals) * 100)


def _parse_summary_json(content: str) -> dict:
    text = (content or "").strip()
    if text.startswith("```"):
        import re

        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _fallback_summary(role: str, items: list[dict]) -> dict:
    avg = mean([i["overall_percent"] for i in items]) if items else 50
    return {
        "overall_feedback": [
            f"Completed a {role or 'mock'} interview with an average score of {round(avg)}%.",
            "Review each question below for technical depth, communication, and sentiment.",
        ],
        "strengths": ["Finished the full interview"],
        "improvements": ["Practice structuring answers with situation → action → result"],
        "speech_tips": [],
        "sentiment_summary": "Analysis used default summary because the AI coach was unavailable.",
    }


async def generate_interview_summary(role: str, items: list[dict]) -> dict:
    if not items:
        return _fallback_summary(role, [])

    lines = []
    for i, row in enumerate(items, 1):
        s = row["scores"]
        lines.append(
            f"Q{i}: {row['question'][:200]}\n"
            f"Scores: tech={s.get('technical_accuracy')}, comm={s.get('communication')}, "
            f"conf={s.get('confidence')}, sentiment={s.get('sentiment')}\n"
            f"Feedback: {s.get('feedback')}"
        )
    human = f"Role: {role}\n\n" + "\n\n".join(lines[:12])

    try:
        response, _ = await ainvoke_with_model_fallback(
            [SystemMessage(content=SUMMARY_PROMPT), HumanMessage(content=human)],
            temperature=0.3,
        )
        parsed = _parse_summary_json(message_text(response))
        if parsed.get("overall_feedback"):
            return parsed
    except Exception as exc:
        logger.exception("Interview summary generation failed: %s", exc)

    return _fallback_summary(role, items)


def _apply_scores_to_answer(answer: Answer, scores: dict) -> None:
    feedback = scores.get("feedback", [])
    feedback_str = json.dumps(feedback) if isinstance(feedback, list) else str(feedback)

    answer.technical_score = float(scores.get("technical_accuracy", 0.5))
    answer.communication_score = float(scores.get("communication", 0.5))
    answer.grammar_score = float(scores.get("grammar", 0.5))
    answer.confidence_score = float(scores.get("confidence", 0.5))
    answer.similarity_score = float(scores.get("similarity_score", 0.0))
    answer.sentiment_score = float(scores.get("sentiment", 0.5))
    answer.ai_feedback = feedback_str


async def run_interview_analysis(db: Session, interview: Interview) -> dict[str, Any]:
    questions = (
        db.query(Question)
        .filter(Question.interview_id == interview.id)
        .order_by(Question.id.asc())
        .all()
    )
    if not questions:
        raise ValueError("No questions found for this interview")

    items: list[dict] = []
    for q in questions:
        ans = db.query(Answer).filter(Answer.question_id == q.id).first()
        if not ans or not (ans.answer_text or "").strip():
            raise ValueError("All questions must be answered before analysis")

        speech = ans.speech_metrics or {}
        if not speech:
            speech = {
                "answer_mode": getattr(ans, "answer_mode", None) or "text",
                "duration_sec": getattr(ans, "speech_duration_sec", None),
                "pause_count": getattr(ans, "pause_count", 0) or 0,
                "filler_count": getattr(ans, "filler_count", 0) or 0,
                "vocabulary_score": getattr(ans, "vocabulary_score", None),
                "words_per_minute": getattr(ans, "words_per_minute", None),
                "fluency_score": 0.5,
            }

        scores = await evaluate_answer(
            question=q.question_text or "",
            answer=ans.answer_text or "",
            expected=q.expected_answer or "",
            speech_metrics=speech,
        )
        local_sentiment = analyze_sentiment_local(ans.answer_text or "")
        try:
            model_sent = float(scores.get("sentiment", local_sentiment))
        except (TypeError, ValueError):
            model_sent = local_sentiment
        scores["sentiment"] = round((model_sent * 0.7 + local_sentiment * 0.3), 3)

        _apply_scores_to_answer(ans, scores)
        overall = _overall_percent(scores)
        items.append(
            {
                "question_id": q.id,
                "question": q.question_text or "",
                "answer": ans.answer_text or "",
                "scores": scores,
                "speech_analysis": speech,
                "overall_percent": overall,
            }
        )

    summary = await generate_interview_summary(interview.role or "", items)
    interview.summary_feedback = json.dumps(summary)

    return {
        "questions": items,
        "summary": summary,
        "average_score": round(mean([i["overall_percent"] for i in items])) if items else 0,
    }
