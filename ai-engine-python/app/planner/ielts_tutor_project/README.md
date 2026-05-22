# IELTS / TOEFL Learning Planner Engine

Adaptive Unlock-aware Mastery-guided Planner for IELTS / TOEFL preparation systems.

The planner decides **what the learner should study today**. A downstream RAG module can use each planned task's `task_id`, `module`, and `resource_query` to retrieve materials and generate explanations, drills, feedback, or mock practice.

## Quick Start

```bash
python examples/demo_planner.py
```

## Core API

```python
from learning_planner import LearningPlanner, UserProfile, TaskFeedback, build_ielts_task_graph

planner = LearningPlanner(build_ielts_task_graph())

profile = UserProfile(
    prep_days=7,
    daily_study_minutes=120,
    target_exam="IELTS",
    weak_modules=["writing", "speaking"],
)

initial_plan = planner.generate_initial_plan(profile)

replanned = planner.replan_after_feedback(
    profile,
    initial_plan,
    [TaskFeedback(task_id="foundation_sentence_structure", mastery_score=82)],
    current_day=1,
)
```

## Algorithm

The planner models learning content as a DAG. A task can only be planned after all prerequisites have been completed or scheduled on earlier days.

Priority combines:

- base learning value
- weak-module bonus
- downstream unlock score
- urgency
- difficulty penalty
- time-cost penalty
- review priority for low mastery feedback

If a learner's mastery score is below the threshold, the planner generates a review task and blocks downstream dependent tasks until mastery is recovered.
