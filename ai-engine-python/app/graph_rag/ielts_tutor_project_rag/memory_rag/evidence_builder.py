"""Build explainable evidence packs from retrieved memories."""

from __future__ import annotations


class EvidenceBuilder:
    def build_evidence_pack(
        self,
        query: str,
        expanded_skills: list[str],
        retrieved_memories: list[dict],
        mastery_state: dict[str, float],
    ) -> dict:
        weak_skills = [skill for skill, score in mastery_state.items() if score < 0.55]
        top_memories = retrieved_memories[:3]
        evidence_lines = []
        for memory in top_memories:
            label = memory.get("task_id") or memory.get("memory_type")
            evidence_lines.append(
                f"{label}: {memory.get('content')} "
                f"(score={memory.get('retrieval_score')}, reasons={', '.join(memory.get('retrieval_reasons', []))})"
            )

        if not evidence_lines:
            summary = "No user-specific memories were retrieved for this query."
        else:
            summary = "Retrieved user-specific learning evidence: " + " | ".join(evidence_lines)

        return {
            "query": query,
            "expanded_skills": expanded_skills,
            "retrieved_memories": retrieved_memories,
            "evidence_summary": summary,
            "mastery_state": mastery_state,
            "low_mastery_skills": weak_skills,
        }
