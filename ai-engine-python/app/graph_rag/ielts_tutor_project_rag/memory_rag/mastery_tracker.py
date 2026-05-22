"""Rule-based mastery tracking for learner-modeling signals."""

from __future__ import annotations


class MasteryTracker:
    """Estimate skill mastery from memory evidence.

    The values are prototype-friendly signals, not psychometric claims. They
    help the RAG layer prioritize skills that appear weak, recent, or repeated.
    """

    def __init__(self, default_mastery: float = 0.65):
        self.default_mastery = default_mastery

    def build_mastery_state(self, memories: list[dict]) -> dict[str, float]:
        mastery: dict[str, float] = {}
        penalties: dict[str, float] = {}
        boosts: dict[str, float] = {}

        for memory in memories:
            metadata = memory.get("metadata", {})
            memory_type = memory.get("memory_type")
            skills = self._memory_skills(memory)

            if memory_type == "mastery_update":
                for skill, value in metadata.get("mastery_scores", {}).items():
                    mastery[skill] = self._clamp(float(value))

            for skill in skills:
                mastery.setdefault(skill, self.default_mastery)

                if memory_type == "weakness":
                    penalties[skill] = penalties.get(skill, 0.0) + 0.16
                if memory_type in {"task_feedback", "essay_feedback", "speaking_feedback"}:
                    score = memory.get("score")
                    if score is not None:
                        score_penalty = max(0.0, 65.0 - float(score)) / 100.0
                        penalties[skill] = penalties.get(skill, 0.0) + min(score_penalty, 0.25)
                if memory_type == "socratic_dialogue":
                    diagnosis = str(metadata.get("diagnosis") or memory.get("content") or "").lower()
                    if "gap" in diagnosis or "failed" in diagnosis or "unclear" in diagnosis:
                        penalties[skill] = penalties.get(skill, 0.0) + 0.12
                if memory_type == "planner_result" and metadata.get("completed"):
                    boosts[skill] = boosts.get(skill, 0.0) + 0.08

        for skill in set(mastery) | set(penalties) | set(boosts):
            current = mastery.get(skill, self.default_mastery)
            mastery[skill] = self._clamp(current - penalties.get(skill, 0.0) + boosts.get(skill, 0.0))

        return dict(sorted(mastery.items(), key=lambda item: item[1]))

    def low_mastery_boost(self, skill: str | None, mastery_state: dict[str, float]) -> float:
        if not skill or skill not in mastery_state:
            return 0.0
        mastery = mastery_state[skill]
        if mastery >= 0.65:
            return 0.0
        return round((0.65 - mastery) * 1.5, 4)

    def _memory_skills(self, memory: dict) -> list[str]:
        skills = []
        if memory.get("skill"):
            skills.append(memory["skill"])
        skills.extend(memory.get("metadata", {}).get("weak_skills", []))
        return self._unique(skills)

    def _unique(self, values) -> list[str]:
        result = []
        seen = set()
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _clamp(self, value: float) -> float:
        return round(max(0.05, min(0.95, value)), 2)
