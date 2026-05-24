"""Analyze spoken-answer transcripts: fillers, pauses, vocabulary, pace."""

from __future__ import annotations

import re
from typing import Any, Optional

FILLER_PATTERN = re.compile(
    r"\b(?:um+|uh+|er+|ah+|like|you know|sort of|kind of|basically|actually|i mean|so yeah)\b",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"[a-zA-Z']+")


def analyze_speech(
    text: str,
    *,
    duration_sec: Optional[float] = None,
    pause_count: int = 0,
    answer_mode: str = "text",
) -> dict[str, Any]:
    cleaned = (text or "").strip()
    words = WORD_PATTERN.findall(cleaned.lower())
    total = len(words)
    unique = len(set(words)) if words else 0

    filler_matches = FILLER_PATTERN.findall(cleaned)
    filler_count = len(filler_matches)
    filler_samples = list(dict.fromkeys(m.lower() for m in filler_matches))[:12]

    vocabulary_score = 0.0
    if total > 0:
        richness = unique / total
        vocabulary_score = min(1.0, round(richness * 1.15 + min(total / 80, 0.15), 3))

    wpm = None
    if duration_sec and duration_sec > 0 and total > 0:
        wpm = round(total / duration_sec * 60, 1)

    filler_rate = (filler_count / max(total, 1)) * 100
    fluency_score = max(0.0, min(1.0, 1.0 - filler_rate / 8 - pause_count * 0.04))

    return {
        "answer_mode": answer_mode,
        "duration_sec": duration_sec,
        "pause_count": int(pause_count or 0),
        "filler_count": filler_count,
        "filler_words": filler_samples,
        "word_count": total,
        "unique_word_count": unique,
        "vocabulary_score": vocabulary_score,
        "words_per_minute": wpm,
        "fluency_score": round(fluency_score, 3),
        "filler_rate_percent": round(filler_rate, 2),
    }


POSITIVE_WORDS = frozenset(
    {
        "achieved", "success", "successful", "improved", "confident", "excited",
        "enjoyed", "learned", "led", "delivered", "built", "solved", "strong",
        "positive", "growth", "impact", "collaborated", "optimized", "scaled",
    }
)
NEGATIVE_WORDS = frozenset(
    {
        "failed", "struggled", "difficult", "problem", "issue", "weak", "nervous",
        "unsure", "lack", "missing", "delayed", "blocked", "confused", "mistake",
        "unable", "hard", "stress", "worried",
    }
)


def analyze_sentiment_local(text: str) -> float:
    """Fast lexical sentiment 0.0–1.0 (no API)."""
    words = WORD_PATTERN.findall((text or "").lower())
    if not words:
        return 0.5
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.55
    raw = (pos - neg) / max(total, 1)
    return round(max(0.0, min(1.0, 0.5 + raw * 0.35)), 3)


def speech_summary_for_eval(metrics: dict[str, Any]) -> str:
    if not metrics or metrics.get("answer_mode") != "voice":
        return ""
    return (
        f"Voice delivery: {metrics.get('duration_sec', '?')}s, "
        f"{metrics.get('words_per_minute', '?')} WPM, "
        f"{metrics.get('pause_count', 0)} pauses, "
        f"{metrics.get('filler_count', 0)} fillers ({', '.join(metrics.get('filler_words') or []) or 'none'}), "
        f"vocabulary richness {metrics.get('vocabulary_score', 0)}, "
        f"fluency {metrics.get('fluency_score', 0)}."
    )
