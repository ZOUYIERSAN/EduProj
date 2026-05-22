"""Lightweight learning skill graph for Memory RAG expansion."""

from __future__ import annotations

import re
from typing import Iterable


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class LearningSkillGraph:
    """A tiny in-memory graph of IELTS / TOEFL learning skills.

    This is intentionally local and dependency-free. It gives the prototype a
    GraphRAG-style expansion step without requiring a graph database.
    """

    def __init__(self, graph: dict[str, list[str]] | None = None):
        self.graph = graph or {
            "argument_development": ["causal_chain", "example_explanation", "thesis_connection", "reasoning_gap"],
            "causal_chain": ["argument_development", "example_explanation", "logical_progression"],
            "example_explanation": ["argument_development", "thesis_connection", "specific_evidence"],
            "thesis_connection": ["argument_development", "task_response", "position_clarity"],
            "coherence": ["paragraph_structure", "logical_progression", "cohesive_devices"],
            "paragraph_structure": ["coherence", "topic_sentence", "logical_progression"],
            "task_response": ["position_clarity", "idea_support", "thesis_connection"],
            "position_clarity": ["task_response", "thesis_connection"],
            "idea_support": ["task_response", "specific_evidence", "example_explanation"],
            "reasoning_depth": ["argument_development", "causal_chain", "reasoning_gap"],
            "reasoning_gap": ["argument_development", "causal_chain", "thesis_connection"],
        }
        self.aliases = {
            "argument": "argument_development",
            "arguments": "argument_development",
            "development": "argument_development",
            "causal": "causal_chain",
            "cause": "causal_chain",
            "chain": "causal_chain",
            "example": "example_explanation",
            "examples": "example_explanation",
            "thesis": "thesis_connection",
            "coherence": "coherence",
            "paragraph": "paragraph_structure",
            "structure": "paragraph_structure",
            "task_response": "task_response",
            "position": "position_clarity",
            "support": "idea_support",
            "evidence": "specific_evidence",
            "reasoning": "reasoning_depth",
            "gap": "reasoning_gap",
        }

    def expand_query(self, query: str, memory_skills: Iterable[str | None] | None = None, depth: int = 1) -> list[str]:
        """Return skills directly or graph-neighbor related to a query."""
        seeds = self.detect_skills(query)
        memory_skill_set = {skill for skill in (memory_skills or []) if skill}
        seeds.update(skill for skill in memory_skill_set if skill in self._query_terms(query))

        expanded = set(seeds)
        frontier = set(seeds)
        for _ in range(max(depth, 0)):
            next_frontier = set()
            for skill in frontier:
                next_frontier.update(self.graph.get(skill, []))
            expanded.update(next_frontier)
            frontier = next_frontier

        return sorted(expanded)

    def detect_skills(self, text: str) -> set[str]:
        terms = self._query_terms(text)
        skills = set()
        normalized_text = " ".join(terms)
        for skill in self.graph:
            if skill in terms or skill.replace("_", " ") in normalized_text:
                skills.add(skill)
        for term in terms:
            if term in self.aliases:
                skills.add(self.aliases[term])
        return skills

    def neighbors(self, skill: str) -> list[str]:
        return list(self.graph.get(skill, []))

    def _query_terms(self, text: str) -> set[str]:
        return {token.lower() for token in TOKEN_RE.findall(text or "")}
