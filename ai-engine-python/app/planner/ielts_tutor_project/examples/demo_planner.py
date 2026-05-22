from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from learning_planner import LearningPlanner, TaskFeedback, UserProfile, build_ielts_task_graph


def main() -> None:
    planner = LearningPlanner(build_ielts_task_graph())
    profile = UserProfile(
        prep_days=7,
        daily_study_minutes=120,
        target_exam="IELTS",
        weak_modules=["writing", "speaking"],
        current_level="B1-B2",
    )

    initial_plan = planner.generate_initial_plan(profile)
    print("=== Initial Plan ===")
    print(json.dumps(initial_plan, indent=2, ensure_ascii=False))

    day_1_feedback = [
        TaskFeedback(task_id="foundation_sentence_structure", mastery_score=82, minutes_spent=45),
        TaskFeedback(task_id="speaking_part1_fluency", mastery_score=58, minutes_spent=35),
    ]
    replanned = planner.replan_after_feedback(profile, initial_plan, day_1_feedback, current_day=1)
    print("\n=== Replanned After Day 1 Feedback ===")
    print(json.dumps(replanned, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
