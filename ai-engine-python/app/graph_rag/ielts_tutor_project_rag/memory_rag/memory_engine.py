"""Product-level interface for the Learning Memory RAG module."""

from __future__ import annotations

from .context_builder import MemoryContextBuilder
from .evidence_builder import EvidenceBuilder
from .mastery_tracker import MasteryTracker
from .memory_extractor import MemoryExtractor
from .memory_schema import create_memory, validate_memory
from .memory_store import JSONLMemoryStore
from .prompt_builder import RAGPromptBuilder
from .rag_pipeline import LearningMemoryRAGPipeline
from .retriever import MemoryRetriever
from .skill_graph import LearningSkillGraph


class LearningMemoryRAG:
    def __init__(self, store_path: str = "data/memory_store.jsonl"):
        self.store = JSONLMemoryStore(store_path)
        self.skill_graph = LearningSkillGraph()
        self.mastery_tracker = MasteryTracker()
        self.extractor = MemoryExtractor(self.skill_graph)
        self.retriever = MemoryRetriever(self.store, self.skill_graph, self.mastery_tracker)
        self.context_builder = MemoryContextBuilder(self.mastery_tracker)
        self.evidence_builder = EvidenceBuilder()
        self.prompt_builder = RAGPromptBuilder()
        self.pipeline = LearningMemoryRAGPipeline(self)

    def add_memory(self, memory: dict) -> str:
        validate_memory(memory)
        return self.store.add_memory(memory)

    def get_user_memories(self, user_id: str) -> list[dict]:
        return self.store.get_user_memories(user_id)

    def retrieve_memories(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        user_memories = self.get_user_memories(user_id)
        expanded_skills = self.skill_graph.expand_query(query, (memory.get("skill") for memory in user_memories))
        mastery_state = self.mastery_tracker.build_mastery_state(user_memories)
        return self.retriever.retrieve_memories(
            query=query,
            user_id=user_id,
            top_k=top_k,
            filters=filters,
            expanded_skills=expanded_skills,
            mastery_state=mastery_state,
        )

    def build_context(self, memories: list[dict]) -> str:
        return self.context_builder.build_context(memories)

    def build_planner_context(self, memories: list[dict]) -> dict:
        return self.context_builder.build_planner_context(memories)

    def build_tutor_context(self, memories: list[dict]) -> str:
        return self.context_builder.build_tutor_context(memories)

    def clear_store(self) -> None:
        self.store.clear_store()

    def extract_and_store_interaction(
        self,
        user_id: str,
        interaction_text: str,
        exam: str = "IELTS",
    ) -> list[str]:
        memories = self.extractor.extract_memories(user_id=user_id, interaction_text=interaction_text, exam=exam)
        return [self.add_memory(memory) for memory in memories]

    def retrieve_memory_evidence(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
    ) -> dict:
        user_memories = self.get_user_memories(user_id)
        expanded_skills = self.skill_graph.expand_query(query, (memory.get("skill") for memory in user_memories))
        mastery_state = self.mastery_tracker.build_mastery_state(user_memories)
        memories = self.retriever.retrieve_memories(
            query=query,
            user_id=user_id,
            top_k=top_k,
            expanded_skills=expanded_skills,
            mastery_state=mastery_state,
        )
        return self.evidence_builder.build_evidence_pack(
            query=query,
            expanded_skills=expanded_skills,
            retrieved_memories=memories,
            mastery_state=mastery_state,
        )

    def build_tutor_prompt(self, query: str, evidence: dict) -> str:
        tutor_context = self.build_tutor_context(evidence["retrieved_memories"])
        return self.prompt_builder.build_tutor_prompt(query, tutor_context, evidence)

    def build_planner_prompt(self, query: str, evidence: dict) -> str:
        planner_context = self.build_planner_context(evidence["retrieved_memories"])
        return self.prompt_builder.build_planner_prompt(query, planner_context, evidence)

    def add_user_profile(
        self,
        user_id: str,
        exam: str,
        target_score: str | None = None,
        current_level: str | None = None,
        weak_modules: list[str] | None = None,
        daily_time_min: int | None = None,
        days_left: int | None = None,
        preferences: list[str] | None = None,
    ) -> str:
        content_parts = [f"User is preparing for {exam}."]
        if target_score:
            content_parts.append(f"Target score is {target_score}.")
        if current_level:
            content_parts.append(f"Current level is {current_level}.")
        if weak_modules:
            content_parts.append(f"Weak modules include {', '.join(weak_modules)}.")
        if preferences:
            content_parts.append(f"Learning preferences: {', '.join(preferences)}.")

        memory = create_memory(
            user_id=user_id,
            memory_type="user_profile",
            exam=exam,
            module=weak_modules[0] if weak_modules else None,
            content=" ".join(content_parts),
            importance=0.9,
            metadata={
                "target_score": target_score,
                "current_level": current_level,
                "weak_modules": weak_modules or [],
                "daily_time_min": daily_time_min,
                "days_left": days_left,
                "preferences": preferences or [],
                "source": "user_profile",
            },
        )
        return self.add_memory(memory)

    def add_task_feedback(
        self,
        user_id: str,
        task_id: str,
        module: str,
        skill: str,
        score: float,
        content: str,
        exam: str = "IELTS",
        importance: float = 0.8,
    ) -> str:
        memory = create_memory(
            user_id=user_id,
            memory_type="task_feedback",
            exam=exam,
            module=module,
            skill=skill,
            task_id=task_id,
            score=score,
            content=content,
            importance=importance,
            metadata={"source": "daily_feedback"},
        )
        return self.add_memory(memory)

    def add_essay_feedback(
        self,
        user_id: str,
        task_id: str,
        score: float,
        weak_skills: list[str],
        content: str,
        exam: str = "IELTS",
        importance: float = 0.9,
    ) -> str:
        memory = create_memory(
            user_id=user_id,
            memory_type="essay_feedback",
            exam=exam,
            module="Writing",
            skill=weak_skills[0] if weak_skills else None,
            task_id=task_id,
            score=score,
            content=content,
            importance=importance,
            metadata={"weak_skills": weak_skills, "source": "essay_feedback"},
        )
        return self.add_memory(memory)

    def add_socratic_dialogue(
        self,
        user_id: str,
        module: str,
        skill: str,
        question: str,
        user_answer: str,
        diagnosis: str,
        exam: str = "IELTS",
        importance: float = 0.7,
    ) -> str:
        memory = create_memory(
            user_id=user_id,
            memory_type="socratic_dialogue",
            exam=exam,
            module=module,
            skill=skill,
            content=f"Tutor asked: {question} User answered: {user_answer} Diagnosis: {diagnosis}",
            importance=importance,
            metadata={
                "question": question,
                "user_answer": user_answer,
                "diagnosis": diagnosis,
                "source": "socratic_tutor",
            },
        )
        return self.add_memory(memory)

    def add_planner_result(
        self,
        user_id: str,
        recommended_tasks: list[str],
        reason: str,
        exam: str = "IELTS",
        importance: float = 0.6,
    ) -> str:
        memory = create_memory(
            user_id=user_id,
            memory_type="planner_result",
            exam=exam,
            content=f"Planner recommended {', '.join(recommended_tasks)}. Reason: {reason}",
            importance=importance,
            metadata={"recommended_tasks": recommended_tasks, "reason": reason, "source": "adaptive_planner"},
        )
        return self.add_memory(memory)
