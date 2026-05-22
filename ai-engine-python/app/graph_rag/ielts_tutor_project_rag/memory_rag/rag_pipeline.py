"""End-to-end Learning Memory RAG pipeline orchestration."""

from __future__ import annotations


class LearningMemoryRAGPipeline:
    def __init__(self, engine):
        self.engine = engine

    def process_interaction_and_retrieve(
        self,
        user_id: str,
        interaction_text: str,
        query: str,
        exam: str = "IELTS",
        top_k: int = 5,
    ) -> dict:
        memory_ids = self.engine.extract_and_store_interaction(
            user_id=user_id,
            interaction_text=interaction_text,
            exam=exam,
        )
        evidence = self.engine.retrieve_memory_evidence(query=query, user_id=user_id, top_k=top_k)
        return {
            "stored_memory_ids": memory_ids,
            "evidence": evidence,
            "planner_context": self.engine.build_planner_context(evidence["retrieved_memories"]),
            "tutor_context": self.engine.build_tutor_context(evidence["retrieved_memories"]),
            "planner_prompt": self.engine.build_planner_prompt(query, evidence),
            "tutor_prompt": self.engine.build_tutor_prompt(query, evidence),
        }
