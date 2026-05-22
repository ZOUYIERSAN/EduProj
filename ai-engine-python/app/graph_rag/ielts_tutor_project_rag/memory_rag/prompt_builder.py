"""Prompt construction for RAG-augmented planner and tutor calls."""

from __future__ import annotations


class RAGPromptBuilder:
    def build_planner_prompt(self, query: str, planner_context: dict, evidence_pack: dict) -> str:
        return "\n".join(
            [
                "You are an adaptive IELTS / TOEFL study planner.",
                "Use only the retrieved user learning memories below as personalization evidence.",
                "",
                f"User query: {query}",
                "",
                "Evidence summary:",
                evidence_pack.get("evidence_summary", ""),
                "",
                f"Skill graph expansion: {evidence_pack.get('expanded_skills', [])}",
                f"Mastery state: {evidence_pack.get('mastery_state', {})}",
                f"Planner context: {planner_context}",
                "",
                "Generate a next-step study plan that prioritizes low mastery skills, recent low-score tasks, and unfinished work.",
            ]
        )

    def build_tutor_prompt(self, query: str, tutor_context: str, evidence_pack: dict) -> str:
        memories = evidence_pack.get("retrieved_memories", [])
        memory_lines = [
            f"- {memory.get('memory_type')} | {memory.get('task_id')} | {memory.get('skill')}: {memory.get('content')}"
            for memory in memories
        ]
        return "\n".join(
            [
                "You are a Socratic IELTS / TOEFL AI tutor.",
                "This is a RAG-augmented prompt built from long-term user learning memory.",
                "",
                f"User query: {query}",
                "",
                "Retrieved user memories:",
                "\n".join(memory_lines) if memory_lines else "- No relevant memories retrieved.",
                "",
                "Evidence summary:",
                evidence_pack.get("evidence_summary", ""),
                "",
                f"Skill graph expansion: {evidence_pack.get('expanded_skills', [])}",
                f"Mastery state: {evidence_pack.get('mastery_state', {})}",
                "",
                "Tutor context:",
                tutor_context,
                "",
                "Instruction: Do not directly provide a full model answer. Ask Socratic questions that help the learner clarify the claim, explain the causal chain, use concrete evidence, and connect the example back to the thesis.",
            ]
        )
