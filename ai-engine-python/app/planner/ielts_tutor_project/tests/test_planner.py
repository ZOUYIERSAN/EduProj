from __future__ import annotations

import json

from learning_planner import LearningPlanner, TaskFeedback, UserProfile, build_ielts_task_graph


def make_planner() -> LearningPlanner:
    return LearningPlanner(build_ielts_task_graph())


def make_profile(**overrides) -> UserProfile:
    values = {
        "prep_days": 7,
        "daily_study_minutes": 120,
        "target_exam": "IELTS",
        "weak_modules": ["writing"],
        "current_level": "intermediate",
    }
    values.update(overrides)
    return UserProfile(**values)


def test_initial_plan_respects_dag_dependencies() -> None:
    planner = make_planner()
    result = planner.generate_initial_plan(make_profile())
    task_by_id = {task.task_id: task for task in build_ielts_task_graph()}
    planned_day = {task["task_id"]: task["day"] for task in result["tasks"]}

    for task_id, day in planned_day.items():
        for prereq in task_by_id[task_id].prerequisites:
            assert prereq in planned_day
            assert planned_day[prereq] < day


def test_daily_budget_is_never_exceeded() -> None:
    result = make_planner().generate_initial_plan(make_profile(daily_study_minutes=90))

    for day in result["plan"]:
        assert day["total_minutes"] <= 90


def test_weak_module_tasks_are_prioritized() -> None:
    writing_plan = make_planner().generate_initial_plan(make_profile(weak_modules=["writing"]))
    reading_plan = make_planner().generate_initial_plan(make_profile(weak_modules=["reading"]))

    writing_first_modules = [task["module"] for task in writing_plan["tasks"][:4]]
    reading_first_modules = [task["module"] for task in reading_plan["tasks"][:4]]

    assert writing_first_modules.count("writing") > reading_first_modules.count("writing")


def test_unlock_aware_foundation_task_is_scheduled_early() -> None:
    result = make_planner().generate_initial_plan(make_profile(weak_modules=["writing"], daily_study_minutes=60))
    days = {task["task_id"]: task["day"] for task in result["tasks"]}

    assert days["foundation_sentence_structure"] < days["writing_task2_structure"]
    foundation = next(task for task in result["tasks"] if task["task_id"] == "foundation_sentence_structure")
    assert foundation["unlock_score"] >= 100


def test_mastery_success_marks_task_completed() -> None:
    planner = make_planner()
    profile = make_profile()
    initial = planner.generate_initial_plan(profile)

    replanned = planner.replan_after_feedback(
        profile,
        initial,
        [TaskFeedback(task_id="foundation_sentence_structure", mastery_score=88)],
        current_day=1,
    )

    assert "foundation_sentence_structure" in replanned["planner_metadata"]["completed_task_ids"]


def test_low_mastery_generates_review_task() -> None:
    planner = make_planner()
    profile = make_profile()
    initial = planner.generate_initial_plan(profile)

    replanned = planner.replan_after_feedback(
        profile,
        initial,
        [TaskFeedback(task_id="foundation_sentence_structure", mastery_score=55)],
        current_day=1,
    )

    review_tasks = [task for task in replanned["tasks"] if task["is_review"]]
    assert review_tasks
    assert review_tasks[0]["review_of"] == "foundation_sentence_structure"
    assert review_tasks[0]["day"] == 2


def test_unmastered_task_does_not_unlock_dependents() -> None:
    planner = make_planner()
    profile = make_profile()
    initial = planner.generate_initial_plan(profile)

    replanned = planner.replan_after_feedback(
        profile,
        initial,
        [TaskFeedback(task_id="foundation_sentence_structure", mastery_score=40)],
        current_day=1,
    )

    future_task_ids = {task["task_id"] for task in replanned["tasks"] if task["day"] > 1}
    assert "writing_task2_structure" not in future_task_ids


def test_replan_preserves_historical_days() -> None:
    planner = make_planner()
    profile = make_profile()
    initial = planner.generate_initial_plan(profile)
    day_1_before = initial["plan"][0]

    replanned = planner.replan_after_feedback(
        profile,
        initial,
        [TaskFeedback(task_id="foundation_sentence_structure", mastery_score=85)],
        current_day=1,
    )

    assert replanned["plan"][0] == day_1_before


def test_output_is_json_serializable_and_contains_rag_fields() -> None:
    result = make_planner().generate_initial_plan(make_profile())

    json.dumps(result)
    assert result["tasks"]
    assert all("resource_query" in task for task in result["tasks"])
    assert all("task_id" in task for task in result["tasks"])
