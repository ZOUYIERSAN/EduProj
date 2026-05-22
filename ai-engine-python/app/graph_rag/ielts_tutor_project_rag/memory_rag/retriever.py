"""Explainable rule-based retrieval over user learning memories."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from .mastery_tracker import MasteryTracker
from .skill_graph import LearningSkillGraph


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")

PLANNER_INTENT_KEYWORDS = {
    "study",
    "tomorrow",
    "next",
    "plan",
    "practice",
    "review",
    "learn",
}

PLANNER_MEMORY_PRIORITIES = {
    "task_feedback",
    "unfinished_task",
    "weakness",
    "essay_feedback",
    "speaking_feedback",
    "planner_result",
    "mastery_update",
    "error_pattern",
    "user_profile",
    "learning_preference",
    "socratic_dialogue",
}


def _tokenize(text: Any) -> set[str]:
    if text is None:
        return set()
    return {token.lower() for token in TOKEN_RE.findall(str(text))}


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


class MemoryRetriever:
    def __init__(
        self,
        store,
        skill_graph: LearningSkillGraph | None = None,
        mastery_tracker: MasteryTracker | None = None,
    ):
        self.store = store
        self.skill_graph = skill_graph or LearningSkillGraph()
        self.mastery_tracker = mastery_tracker or MasteryTracker()

    def retrieve_memories(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict | None = None,
        expanded_skills: list[str] | None = None,
        mastery_state: dict[str, float] | None = None,
    ) -> list[dict]:
        query_tokens = _tokenize(query)
        planner_intent = bool(query_tokens & PLANNER_INTENT_KEYWORDS)
        user_memories = self.store.get_user_memories(user_id)
        expanded_skills = expanded_skills or self.skill_graph.expand_query(
            query,
            (memory.get("skill") for memory in user_memories),
        )
        mastery_state = mastery_state or self.mastery_tracker.build_mastery_state(user_memories)
        scored: list[dict] = []

        for memory in user_memories:
            if not self._passes_filters(memory, filters):
                continue

            score, reasons, breakdown = self._score_memory(
                memory,
                query_tokens,
                planner_intent,
                expanded_skills,
                mastery_state,
            )
            enriched = dict(memory)
            enriched["retrieval_score"] = round(score, 4)
            enriched["score_breakdown"] = {key: round(value, 4) for key, value in breakdown.items()}
            enriched["retrieval_reasons"] = reasons
            scored.append(enriched)

        scored.sort(
            key=lambda item: (
                item["retrieval_score"],
                float(item.get("importance") or 0),
                item.get("timestamp") or "",
            ),
            reverse=True,
        )
        return scored[:top_k]

    def _passes_filters(self, memory: dict, filters: dict | None) -> bool:
        if not filters:
            return True
        for key, expected in filters.items():
            actual = memory.get(key)
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def _score_memory(
        self,
        memory: dict,
        query_tokens: set[str],
        planner_intent: bool,
        expanded_skills: list[str],
        mastery_state: dict[str, float],
    ) -> tuple[float, list[str], dict[str, float]]:
        score = 1.0
        reasons = ["same_user"]
        breakdown = {
            "base_user_match": 1.0,
            "lexical": 0.0,
            "field_match": 0.0,
            "pedagogical_priority": 0.0,
            "recency": 0.0,
            "importance": 0.0,
            "mastery": 0.0,
            "graph_expansion": 0.0,
        }

        content_tokens = _tokenize(memory.get("content"))
        field_text = " ".join(
            str(memory.get(field) or "")
            for field in ("exam", "module", "skill", "task_id", "memory_type")
        )
        field_tokens = _tokenize(field_text)
        metadata_tokens = _tokenize(memory.get("metadata"))

        content_overlap = query_tokens & content_tokens
        field_overlap = query_tokens & field_tokens
        metadata_overlap = query_tokens & metadata_tokens

        if content_overlap:
            boost = 0.45 * len(content_overlap)
            score += boost
            breakdown["lexical"] += boost
            reasons.append(f"content_keyword_overlap:{','.join(sorted(content_overlap))}")

        if field_overlap:
            boost = 0.75 * len(field_overlap)
            score += boost
            breakdown["field_match"] += boost
            reasons.append(f"structured_field_overlap:{','.join(sorted(field_overlap))}")

        if metadata_overlap:
            boost = 0.25 * len(metadata_overlap)
            score += boost
            breakdown["field_match"] += boost
            reasons.append(f"metadata_overlap:{','.join(sorted(metadata_overlap))}")

        importance = float(memory.get("importance") or 0)
        score += importance
        breakdown["importance"] += importance
        reasons.append(f"importance:{importance:.2f}")

        recency_score = self._recency_score(memory.get("timestamp"))
        if recency_score:
            score += recency_score
            breakdown["recency"] += recency_score
            reasons.append(f"recency:{recency_score:.2f}")

        memory_type = memory.get("memory_type")
        if planner_intent and memory_type in PLANNER_MEMORY_PRIORITIES:
            score += 0.8
            breakdown["pedagogical_priority"] += 0.8
            reasons.append("planner_intent_memory_type")

        score_value = memory.get("score")
        if score_value is not None:
            numeric_score = float(score_value)
            if numeric_score < 65:
                score += 0.7
                breakdown["pedagogical_priority"] += 0.7
                reasons.append("low_score_priority")

        # Underscore skills such as argument_development should also match
        # natural queries such as "argument development".
        skill_tokens = _tokenize(str(memory.get("skill") or "").replace("_", " "))
        expanded_skill_overlap = query_tokens & skill_tokens
        if expanded_skill_overlap:
            score += 0.5 * len(expanded_skill_overlap)
            breakdown["field_match"] += 0.5 * len(expanded_skill_overlap)
            reasons.append(f"skill_phrase_overlap:{','.join(sorted(expanded_skill_overlap))}")

        if memory_type == "socratic_dialogue" and {"why", "explain", "improve", "argument", "reasoning"} & query_tokens:
            score += 0.5
            breakdown["pedagogical_priority"] += 0.5
            reasons.append("socratic_tutoring_relevance")

        memory_skills = set()
        if memory.get("skill"):
            memory_skills.add(memory["skill"])
        memory_skills.update(memory.get("metadata", {}).get("weak_skills", []))
        graph_overlap = memory_skills & set(expanded_skills)
        if graph_overlap:
            boost = 0.35 * len(graph_overlap)
            score += boost
            breakdown["graph_expansion"] += boost
            reasons.append(f"skill_graph_overlap:{','.join(sorted(graph_overlap))}")

        mastery_boost = sum(
            self.mastery_tracker.low_mastery_boost(skill, mastery_state)
            for skill in graph_overlap or memory_skills
        )
        if mastery_boost:
            score += mastery_boost
            breakdown["mastery"] += mastery_boost
            reasons.append(f"low_mastery_priority:{mastery_boost:.2f}")

        return score, reasons, breakdown

    def _recency_score(self, timestamp: str | None) -> float:
        parsed = _parse_timestamp(timestamp)
        if not parsed:
            return 0.0
        age_days = max((datetime.now(timezone.utc) - parsed).total_seconds() / 86400, 0)
        return 0.35 * math.exp(-age_days / 30)
