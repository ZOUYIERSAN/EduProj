"""Rule-based extraction of learning memories from raw interactions."""

from __future__ import annotations

import re

from .memory_schema import create_memory
from .skill_graph import LearningSkillGraph


TASK_RE = re.compile(r"\b([WRSLC]\d{3})\b", re.IGNORECASE)
SCORE_RE = re.compile(r"\b(?:score|scored|got|grade|graded)\s*(?:is|was|:)?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)


class MemoryExtractor:
    """Extract prototype learning memories without calling an external LLM."""

    def __init__(self, skill_graph: LearningSkillGraph | None = None):
        self.skill_graph = skill_graph or LearningSkillGraph()

    def extract_memories(self, user_id: str, interaction_text: str, exam: str = "IELTS") -> list[dict]:
        text = interaction_text.strip()
        if not text:
            return []

        lowered = text.lower()
        task_id = self._extract_task_id(text)
        score = self._extract_score(text)
        module = self._extract_module(lowered)
        skills = self.skill_graph.expand_query(text, depth=0)
        primary_skill = skills[0] if skills else None
        is_profile = "target score" in lowered or "current level" in lowered

        memories: list[dict] = []

        if is_profile:
            memories.append(
                create_memory(
                    user_id=user_id,
                    memory_type="user_profile",
                    exam=exam,
                    module=module,
                    content=text,
                    importance=0.75,
                    metadata={"source": "memory_extractor"},
                )
            )

        if not is_profile and self._looks_like_feedback(lowered) and score is not None:
            memories.append(
                create_memory(
                    user_id=user_id,
                    memory_type="task_feedback",
                    exam=exam,
                    module=module,
                    skill=primary_skill,
                    task_id=task_id,
                    score=score,
                    content=text,
                    importance=0.86 if score < 65 else 0.65,
                    metadata={"source": "memory_extractor", "weak_skills": skills},
                )
            )

        if module == "Writing" and ("essay" in lowered or "task 2" in lowered or "body paragraph" in lowered):
            memories.append(
                create_memory(
                    user_id=user_id,
                    memory_type="essay_feedback",
                    exam=exam,
                    module=module,
                    skill=primary_skill,
                    task_id=task_id,
                    score=score,
                    content=text,
                    importance=0.9,
                    metadata={"source": "memory_extractor", "weak_skills": skills},
                )
            )

        if self._looks_like_weakness(lowered) and skills:
            memories.append(
                create_memory(
                    user_id=user_id,
                    memory_type="weakness",
                    exam=exam,
                    module=module,
                    skill=primary_skill,
                    content=f"Extracted recurring weakness: {', '.join(skills)}. Evidence: {text}",
                    importance=0.88,
                    metadata={"source": "memory_extractor", "weak_skills": skills},
                )
            )

        if "prefers" in lowered or "prefer" in lowered:
            preference = self._extract_preference(text)
            memories.append(
                create_memory(
                    user_id=user_id,
                    memory_type="learning_preference",
                    exam=exam,
                    content=f"User prefers {preference}.",
                    importance=0.72,
                    metadata={"source": "memory_extractor", "preference": preference},
                )
            )

        if self._looks_like_socratic(lowered):
            memories.append(
                create_memory(
                    user_id=user_id,
                    memory_type="socratic_dialogue",
                    exam=exam,
                    module=module,
                    skill=primary_skill,
                    content=text,
                    importance=0.78,
                    metadata={
                        "source": "memory_extractor",
                        "diagnosis": self._extract_diagnosis(text),
                        "weak_skills": skills,
                    },
                )
            )

        return self._deduplicate(memories)

    def _extract_task_id(self, text: str) -> str | None:
        match = TASK_RE.search(text)
        return match.group(1).upper() if match else None

    def _extract_score(self, text: str) -> float | None:
        match = SCORE_RE.search(text)
        return float(match.group(1)) if match else None

    def _extract_module(self, lowered: str) -> str | None:
        for module in ("writing", "speaking", "reading", "listening"):
            if module in lowered:
                return module.title()
        if "essay" in lowered or "task 2" in lowered:
            return "Writing"
        return None

    def _looks_like_feedback(self, lowered: str) -> bool:
        return any(term in lowered for term in ("scored", "feedback", "struggled", "graded", "diagnosis"))

    def _looks_like_weakness(self, lowered: str) -> bool:
        return any(term in lowered for term in ("weak", "struggled", "gap", "incomplete", "failed", "recurring"))

    def _looks_like_socratic(self, lowered: str) -> bool:
        return "tutor asked" in lowered or "socratic" in lowered or ("question" in lowered and "answer" in lowered)

    def _extract_preference(self, text: str) -> str:
        match = re.search(r"prefers?\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
        return match.group(1).strip() if match else text.strip()

    def _extract_diagnosis(self, text: str) -> str:
        match = re.search(r"diagnosis\s*:?\s*(.+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else text.strip()

    def _deduplicate(self, memories: list[dict]) -> list[dict]:
        seen = set()
        result = []
        for memory in memories:
            key = (memory["memory_type"], memory.get("task_id"), memory.get("skill"), memory["content"])
            if key not in seen:
                seen.add(key)
                result.append(memory)
        return result
