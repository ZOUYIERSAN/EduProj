# Learning Memory RAG Module

This module is a product-like prototype for the long-term memory layer of an AI IELTS / TOEFL tutor. It stores user-specific learning memories, retrieves relevant memories, and builds structured context for an adaptive planner or Socratic AI tutor.

It is not a normal document QA RAG system. It does not answer generic questions from IELTS materials. Instead, it remembers the learner: goals, current level, weak modules, weak skills, task history, essay feedback, speaking feedback, Socratic dialogue history, preferences, planner outputs, unfinished work, mastery updates, and recurring error patterns.

## Why It Matters

Long-term test preparation creates many small signals: low-score tasks, repeated reasoning gaps, unfinished study items, preferred explanation style, and changing mastery. A normal chatbot forgets these signals across sessions. Learning Memory RAG keeps them in a retrievable memory layer so the tutor can personalize planning, diagnosis, and feedback over time.

The intended learning loop is:

```text
Plan -> Learn -> Diagnose -> Store -> Retrieve -> Replan
```

The upgraded research-style RAG flow is:

```text
Raw interaction
-> Memory Extractor
-> JSONL Memory Store
-> Hybrid Explainable Retriever
-> Evidence Pack
-> Planner / Tutor Context
-> RAG-Augmented Prompt
```

## Core Functions

- Store learning memories as JSON-style Python dictionaries.
- Extract structured learning memories from raw tutoring interactions.
- Retrieve user-specific memories with hybrid explainable scoring.
- Expand query skills with a lightweight learning skill graph.
- Estimate skill mastery from low-score tasks, weaknesses, and Socratic diagnoses.
- Build evidence packs with retrieval reasons and score breakdowns.
- Build structured planner context for the adaptive study planner.
- Build tutor context for personalized Socratic teaching.
- Build RAG-augmented planner and tutor prompts without calling an external LLM.

## Technical Idea

Learning Memory RAG stores dynamic user-specific learning states and retrieves them when the planner or tutor needs context. This module is separate from a future Static Knowledge RAG system that may store IELTS / TOEFL rubrics, examples, strategies, and study materials.

The retrieval layer is deliberately explainable. Each returned memory includes:

```python
{
    "retrieval_score": 4.82,
    "score_breakdown": {
        "lexical": 1.2,
        "field_match": 1.5,
        "pedagogical_priority": 0.9,
        "recency": 0.3,
        "importance": 0.9,
        "mastery": 0.4,
        "graph_expansion": 0.35
    },
    "retrieval_reasons": [...]
}
```

This makes the module useful for competition demos because the system can explain why it retrieved a low-score task, a recurring weakness, or a Socratic dialogue.

The architecture is:

```text
Memory RAG: remembers the user.
Static RAG: remembers IELTS / TOEFL materials.
Planner: decides what to study next.
LLM Tutor: explains, questions, diagnoses, and interacts.
```

## Project Structure

```text
ielts_tutor_project/
├── data/
│   ├── memory_store.jsonl
│   └── sample_memories.jsonl
├── memory_rag/
│   ├── __init__.py
│   ├── evidence_builder.py
│   ├── mastery_tracker.py
│   ├── memory_extractor.py
│   ├── memory_schema.py
│   ├── memory_store.py
│   ├── prompt_builder.py
│   ├── rag_pipeline.py
│   ├── retriever.py
│   ├── skill_graph.py
│   ├── context_builder.py
│   └── memory_engine.py
├── tests/
│   └── test_deep_memory_rag.py
├── run_deep_rag_demo.py
├── run_memory_demo.py
└── README_memory_rag.md
```

## How To Run

From this directory:

```bash
python run_memory_demo.py
```

For the deeper competition-style RAG demonstration:

```bash
python run_deep_rag_demo.py
```

The demo seeds a local JSONL memory store with a sample learner profile, Writing weakness, low-score Task 2 feedback, essay feedback, Socratic dialogue history, a learning preference, and a planner result.

It then runs:

```python
memory_rag.retrieve_memories(
    query="What should I study tomorrow?",
    user_id="user_001",
    top_k=5
)
```

and:

```python
memory_rag.retrieve_memories(
    query="Help me improve IELTS Writing Task 2 argument development.",
    user_id="user_001",
    top_k=5
)
```

The output shows retrieved user memories, retrieval scores, retrieval reasons, planner context, and tutor context.

The deep demo additionally prints:

```text
[1] Extracted Learning Memories
[2] Retrieved Memories
[3] Retrieval Score Breakdown
[4] Skill Graph Expansion
[5] Mastery State
[6] Planner Context
[7] RAG-Augmented Tutor Prompt
```

## Example Integration

```python
from memory_rag import LearningMemoryRAG

memory_rag = LearningMemoryRAG()

memory_ids = memory_rag.extract_and_store_interaction(
    user_id="user_001",
    interaction_text="User scored 55 on W003 IELTS Writing Task 2 and struggled with argument development.",
)

memories = memory_rag.retrieve_memories(
    query="What should the user study next?",
    user_id="user_001",
    top_k=5,
)

planner_context = memory_rag.build_planner_context(memories)
```

Later, an adaptive planner can use `planner_context` to generate the next study plan.

```python
memories = memory_rag.retrieve_memories(
    query="Generate Socratic questions for IELTS Task 2 argument development.",
    user_id="user_001",
    top_k=5,
)

tutor_context = memory_rag.build_tutor_context(memories)
```

Later, an LLM tutor can use `tutor_context` to generate personalized Socratic questions.

The research-style interface can also return an evidence pack:

```python
evidence = memory_rag.retrieve_memory_evidence(
    query="Generate Socratic questions for IELTS Task 2 argument development.",
    user_id="user_001",
    top_k=5,
)

tutor_prompt = memory_rag.build_tutor_prompt(
    query="Generate Socratic questions for IELTS Task 2 argument development.",
    evidence=evidence,
)
```

This is the RAG augmentation boundary: retrieved memories, graph-expanded skills, mastery state, and evidence summary are all inserted into a prompt-ready context.

## Run Tests

```bash
python -m unittest discover tests
```

## Future Extensions

- Add embedding-based vector retrieval.
- Add a static IELTS / TOEFL knowledge RAG module.
- Connect to an adaptive planner.
- Connect to an LLM tutor.
- Add GraphRAG over test skills and knowledge points.
- Add DKT or mastery tracking for skill-level progress estimation.
