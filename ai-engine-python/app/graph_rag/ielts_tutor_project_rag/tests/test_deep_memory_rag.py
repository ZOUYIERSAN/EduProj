from __future__ import annotations

import json
import unittest
from pathlib import Path

from memory_rag import LearningMemoryRAG, LearningSkillGraph, MemoryExtractor
from memory_rag.memory_schema import create_memory
from memory_rag.memory_store import JSONLMemoryStore


TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_store_path(name: str) -> Path:
    path = TEST_DATA_DIR / name
    path.unlink(missing_ok=True)
    return path


class DeepMemoryRAGTests(unittest.TestCase):
    def tearDown(self):
        for path in TEST_DATA_DIR.glob("__test_*.jsonl"):
            path.unlink(missing_ok=True)

    def test_schema_validation_rejects_bad_memory_type(self):
        with self.assertRaises(ValueError):
            create_memory(user_id="u1", memory_type="bad_type", content="bad")

    def test_jsonl_store_skips_invalid_json(self):
        path = test_store_path("__test_invalid.jsonl")
        path.write_text('{"memory_id": "ok", "user_id": "u1"}\nnot-json\n', encoding="utf-8")
        store = JSONLMemoryStore(str(path))
        memories = store.load_all_memories()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["memory_id"], "ok")

    def test_extractor_finds_low_score_weak_skill_and_preference(self):
        extractor = MemoryExtractor()
        memories = extractor.extract_memories(
            user_id="u1",
            interaction_text=(
                "User scored 55 on W003 IELTS Writing Task 2 essay. "
                "The user struggled with argument development and causal chain. "
                "User prefers logic-based explanation."
            ),
        )
        memory_types = {memory["memory_type"] for memory in memories}
        self.assertIn("task_feedback", memory_types)
        self.assertIn("essay_feedback", memory_types)
        self.assertIn("weakness", memory_types)
        self.assertIn("learning_preference", memory_types)

    def test_skill_graph_expands_argument_development(self):
        graph = LearningSkillGraph()
        expanded = graph.expand_query("Improve Task 2 argument development")
        self.assertIn("argument_development", expanded)
        self.assertIn("causal_chain", expanded)
        self.assertIn("example_explanation", expanded)

    def test_retriever_prioritizes_writing_task_2_memory(self):
        memory_rag = LearningMemoryRAG(store_path=str(test_store_path("__test_retriever.jsonl")))
        memory_rag.add_task_feedback(
            user_id="u1",
            task_id="W003",
            module="Writing",
            skill="argument_development",
            score=55,
            content="User scored 55 on IELTS Writing Task 2 and struggled with argument development.",
        )
        memory_rag.add_socratic_dialogue(
            user_id="u1",
            module="Writing",
            skill="argument_development",
            question="Why does the example prove the claim?",
            user_answer="Because it is serious.",
            diagnosis="Reasoning gap between example and claim.",
        )
        memories = memory_rag.retrieve_memories("Help me improve IELTS Writing Task 2 argument development.", "u1")
        self.assertEqual(memories[0]["task_id"], "W003")
        self.assertIn("score_breakdown", memories[0])
        self.assertTrue(any(memory["memory_type"] == "socratic_dialogue" for memory in memories))

    def test_mastery_and_prompt_are_in_evidence(self):
        memory_rag = LearningMemoryRAG(store_path=str(test_store_path("__test_evidence.jsonl")))
        memory_rag.extract_and_store_interaction(
            user_id="u1",
            interaction_text=(
                "User scored 55 on W003 IELTS Writing Task 2 essay. "
                "The essay struggled with argument development, causal chain, and thesis connection."
            ),
        )
        evidence = memory_rag.retrieve_memory_evidence("What should I study tomorrow?", "u1")
        prompt = memory_rag.build_tutor_prompt("What should I study tomorrow?", evidence)
        self.assertIn("mastery_state", evidence)
        self.assertIn("Retrieved user memories", prompt)
        self.assertIn("Do not directly provide a full model answer", prompt)

    def test_deep_demo_style_pipeline_returns_json_serializable_evidence(self):
        memory_rag = LearningMemoryRAG(store_path=str(test_store_path("__test_pipeline.jsonl")))
        result = memory_rag.pipeline.process_interaction_and_retrieve(
            user_id="u1",
            interaction_text="User scored 55 on W003 IELTS Writing essay and struggled with argument development.",
            query="Help me improve argument development.",
            top_k=3,
        )
        json.dumps(result, ensure_ascii=False)
        self.assertIn("planner_prompt", result)
        self.assertIn("tutor_prompt", result)


if __name__ == "__main__":
    unittest.main()
