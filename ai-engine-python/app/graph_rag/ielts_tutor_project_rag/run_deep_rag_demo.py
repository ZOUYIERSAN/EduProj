from __future__ import annotations

import json
from pathlib import Path

from memory_rag import LearningMemoryRAG


BASE_DIR = Path(__file__).resolve().parent
DEMO_STORE = BASE_DIR / "data" / "memory_store.jsonl"
USER_ID = "user_001"


RAW_INTERACTIONS = [
    (
        "User profile: preparing for IELTS. Target score is 7.0. Current level is 6.0. "
        "Writing is currently the weakest module. The user prefers logic-based explanation rather than memorizing templates."
    ),
    (
        "Daily feedback: User scored 55 on W003 IELTS Writing Task 2 essay. "
        "The essay struggled with argument development, causal chain, example explanation, and thesis connection."
    ),
    (
        "Socratic dialogue. Tutor asked: Why does this example prove your topic sentence? "
        "User answer: Because it shows the problem is serious. "
        "Diagnosis: The user failed to explain the reasoning gap between the example and the claim."
    ),
]


def print_section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def print_retrieved(memories: list[dict]) -> None:
    print_json(
        [
            {
                "memory_id": memory["memory_id"],
                "memory_type": memory["memory_type"],
                "module": memory.get("module"),
                "skill": memory.get("skill"),
                "task_id": memory.get("task_id"),
                "score": memory.get("score"),
                "retrieval_score": memory.get("retrieval_score"),
                "score_breakdown": memory.get("score_breakdown"),
                "retrieval_reasons": memory.get("retrieval_reasons"),
                "content": memory.get("content"),
            }
            for memory in memories
        ]
    )


def run_query(memory_rag: LearningMemoryRAG, query: str) -> None:
    evidence = memory_rag.retrieve_memory_evidence(query=query, user_id=USER_ID, top_k=7)
    memories = evidence["retrieved_memories"]

    print_section(f"Query: {query}")
    print("\n[2] Retrieved Memories")
    print_retrieved(memories)

    print("\n[3] Retrieval Score Breakdown")
    print_json(
        {
            memory["memory_id"]: memory.get("score_breakdown", {})
            for memory in memories
        }
    )

    print("\n[4] Skill Graph Expansion")
    print_json(evidence["expanded_skills"])

    print("\n[5] Mastery State")
    print_json(evidence["mastery_state"])

    print("\n[6] Planner Context")
    planner_context = memory_rag.build_planner_context(memories)
    print_json(planner_context)

    print("\nEvidence Pack Summary")
    print(evidence["evidence_summary"])

    print("\n[7] RAG-Augmented Tutor Prompt")
    print(memory_rag.build_tutor_prompt(query, evidence))

    print("\nRAG-Augmented Planner Prompt")
    print(memory_rag.build_planner_prompt(query, evidence))


def main() -> None:
    memory_rag = LearningMemoryRAG(store_path=str(DEMO_STORE))
    memory_rag.clear_store()

    print_section("[1] Extracted Learning Memories")
    for interaction in RAW_INTERACTIONS:
        memory_ids = memory_rag.extract_and_store_interaction(USER_ID, interaction)
        print_json({"raw_interaction": interaction, "stored_memory_ids": memory_ids})

    run_query(memory_rag, "What should I study tomorrow?")
    run_query(memory_rag, "Help me improve Task 2 argument development.")


if __name__ == "__main__":
    main()
