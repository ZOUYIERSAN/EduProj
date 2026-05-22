from __future__ import annotations

import json
from pathlib import Path

from memory_rag import LearningMemoryRAG
from memory_rag.memory_schema import create_memory


BASE_DIR = Path(__file__).resolve().parent
DEMO_STORE = BASE_DIR / "data" / "memory_store.jsonl"
USER_ID = "user_001"


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def seed_demo_memories(memory_rag: LearningMemoryRAG) -> None:
    memory_rag.clear_store()

    memory_rag.add_user_profile(
        user_id=USER_ID,
        exam="IELTS",
        target_score="7.0",
        current_level="6.0",
        weak_modules=["Writing"],
        daily_time_min=60,
        days_left=45,
        preferences=["logic-based explanation rather than memorizing templates"],
    )

    memory_rag.add_memory(
        create_memory(
            user_id=USER_ID,
            memory_type="weakness",
            exam="IELTS",
            module="Writing",
            skill="argument_development",
            content="Writing is the user's weakest module. Argument development and reasoning depth are recurring weaknesses.",
            importance=0.9,
            metadata={"source": "diagnostic_summary", "weak_skills": ["argument_development", "reasoning_depth"]},
        )
    )

    memory_rag.add_task_feedback(
        user_id=USER_ID,
        task_id="W003",
        module="Writing",
        skill="argument_development",
        score=55,
        content="User scored 55 on W003 IELTS Writing Task 2 essay structure and struggled with argument development.",
        importance=0.92,
    )

    memory_rag.add_essay_feedback(
        user_id=USER_ID,
        task_id="W003",
        score=55,
        weak_skills=["argument_development", "example_explanation", "thesis_connection"],
        content=(
            "Essay feedback for W003: the main claim was understandable, but the causal chain was incomplete. "
            "The example was not clearly connected back to the thesis."
        ),
        importance=0.95,
    )

    memory_rag.add_socratic_dialogue(
        user_id=USER_ID,
        module="Writing",
        skill="argument_development",
        question="Why does this example prove your topic sentence?",
        user_answer="Because it shows the problem is serious.",
        diagnosis="The user noticed the topic but failed to explain the reasoning gap between the example and the claim.",
        importance=0.82,
    )

    memory_rag.add_memory(
        create_memory(
            user_id=USER_ID,
            memory_type="learning_preference",
            exam="IELTS",
            content="User prefers logic-based explanation rather than memorizing templates.",
            importance=0.78,
            metadata={
                "preference": "logic-based explanation rather than memorizing templates",
                "source": "onboarding",
            },
        )
    )

    memory_rag.add_planner_result(
        user_id=USER_ID,
        recommended_tasks=["Review W003", "Practice Task 2 causal chain drill", "Revise one body paragraph"],
        reason="Writing is weak and W003 showed low score argument development problems.",
        importance=0.68,
    )


def run_query(memory_rag: LearningMemoryRAG, query: str, top_k: int = 7) -> list[dict]:
    print_section(f"Query: {query}")
    memories = memory_rag.retrieve_memories(query=query, user_id=USER_ID, top_k=top_k)

    print("\nRetrieved memories:")
    print_json(
        [
            {
                "memory_id": memory["memory_id"],
                "memory_type": memory["memory_type"],
                "module": memory.get("module"),
                "skill": memory.get("skill"),
                "task_id": memory.get("task_id"),
                "score": memory.get("score"),
                "content": memory["content"],
                "retrieval_score": memory["retrieval_score"],
                "score_breakdown": memory.get("score_breakdown"),
                "retrieval_reasons": memory["retrieval_reasons"],
            }
            for memory in memories
        ]
    )
    return memories


def main() -> None:
    memory_rag = LearningMemoryRAG(store_path=str(DEMO_STORE))
    seed_demo_memories(memory_rag)

    query_1 = "What should I study tomorrow?"
    memories_1 = run_query(memory_rag, query_1)

    print("\nGeneral context:")
    print(memory_rag.build_context(memories_1))

    print("\nPlanner context:")
    print_json(memory_rag.build_planner_context(memories_1))

    print("\nTutor context:")
    print(memory_rag.build_tutor_context(memories_1))

    query_2 = "Help me improve IELTS Writing Task 2 argument development."
    memories_2 = run_query(memory_rag, query_2)

    print("\nTutor context:")
    print(memory_rag.build_tutor_context(memories_2))


if __name__ == "__main__":
    main()
