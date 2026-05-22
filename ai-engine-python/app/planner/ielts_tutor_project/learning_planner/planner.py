from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import replace
from typing import Any, Iterable

from .models import DailyPlan, PlannedTask, PlannerResult, TaskFeedback, TaskNode, UserProfile


class LearningPlanner:
    """Adaptive unlock-aware mastery-guided planner for exam preparation DAGs."""

    def __init__(
        self,
        tasks: Iterable[TaskNode],
        *,
        unlock_weight: float = 0.35,
        weak_module_bonus: float = 18.0,
        review_bonus: float = 35.0,
        urgency_weight: float = 7.0,
        difficulty_weight: float = 2.5,
        time_cost_weight: float = 0.08,
    ) -> None:
        self.tasks = {task.task_id: task for task in tasks}
        self.unlock_weight = unlock_weight
        self.weak_module_bonus = weak_module_bonus
        self.review_bonus = review_bonus
        self.urgency_weight = urgency_weight
        self.difficulty_weight = difficulty_weight
        self.time_cost_weight = time_cost_weight
        self.children = self._build_children()
        self._validate_graph()
        self.unlock_scores = self._compute_unlock_scores()

    def generate_initial_plan(self, user_profile: UserProfile | dict[str, Any]) -> dict[str, Any]:
        profile = self._coerce_user_profile(user_profile)
        return self._plan(
            profile=profile,
            start_day=1,
            completed_task_ids=set(profile.completed_task_ids),
            mastery_scores=dict(profile.mastery_scores),
            review_tasks=[],
            historical_plan=[],
            event="initial_plan",
        )

    def replan_after_feedback(
        self,
        user_profile: UserProfile | dict[str, Any],
        existing_plan: dict[str, Any],
        feedback: Iterable[TaskFeedback | dict[str, Any]],
        current_day: int,
    ) -> dict[str, Any]:
        profile = self._coerce_user_profile(user_profile)
        feedback_items = [self._coerce_feedback(item) for item in feedback]
        metadata = existing_plan.get("planner_metadata", {})
        completed_task_ids = set(metadata.get("completed_task_ids", profile.completed_task_ids))
        mastery_scores = dict(metadata.get("mastery_scores", profile.mastery_scores))
        blocked_task_ids = set(metadata.get("blocked_task_ids", []))
        review_tasks = self._load_pending_reviews(existing_plan, current_day)

        for item in feedback_items:
            task = self._lookup_planned_or_base_task(existing_plan, item.task_id)
            mastery_scores[item.task_id] = item.mastery_score
            if task.review_of:
                mastery_scores[task.review_of] = item.mastery_score

            mastered = item.completed and item.mastery_score >= profile.mastery_threshold
            if mastered:
                completed_task_ids.add(item.task_id)
                if task.review_of:
                    completed_task_ids.add(task.review_of)
                    blocked_task_ids.discard(task.review_of)
            else:
                target_id = task.review_of or item.task_id
                completed_task_ids.discard(target_id)
                blocked_task_ids.add(target_id)
                review_tasks.append(self._make_review_task(target_id, current_day + 1, item.mastery_score))

        profile = replace(
            profile,
            completed_task_ids=sorted(completed_task_ids),
            mastery_scores=mastery_scores,
        )
        historical_plan = self._historical_days(existing_plan, current_day)
        result = self._plan(
            profile=profile,
            start_day=current_day + 1,
            completed_task_ids=completed_task_ids,
            mastery_scores=mastery_scores,
            review_tasks=self._dedupe_reviews(review_tasks, completed_task_ids),
            historical_plan=historical_plan,
            event="adaptive_replan",
            blocked_task_ids=blocked_task_ids,
        )
        result["planner_metadata"]["feedback_applied"] = [item.to_dict() for item in feedback_items]
        result["planner_metadata"]["current_day"] = current_day
        return result

    def _plan(
        self,
        *,
        profile: UserProfile,
        start_day: int,
        completed_task_ids: set[str],
        mastery_scores: dict[str, int],
        review_tasks: list[TaskNode],
        historical_plan: list[dict[str, Any]],
        event: str,
        blocked_task_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        blocked_task_ids = blocked_task_ids or set()
        candidate_tasks = self._tasks_for_exam(profile.normalized_exam())
        dynamic_tasks = {task.task_id: task for task in review_tasks}
        all_tasks = {**candidate_tasks, **dynamic_tasks}
        scheduled_ids = set(completed_task_ids)
        future_days: list[DailyPlan] = []
        flat_tasks: list[PlannedTask] = []
        weak_modules = profile.normalized_weak_modules()

        for day in range(start_day, profile.prep_days + 1):
            minutes_left = profile.daily_study_minutes
            day_tasks: list[PlannedTask] = []
            day_start_completed = set(scheduled_ids)

            while minutes_left > 0:
                available = [
                    task
                    for task in all_tasks.values()
                    if task.task_id not in scheduled_ids
                    and task.estimated_minutes <= minutes_left
                    and self._is_available(task, day_start_completed, blocked_task_ids)
                ]
                if not available:
                    break

                selected = max(
                    available,
                    key=lambda task: self._priority_score(task, profile, weak_modules, day, start_day),
                )
                planned = self._to_planned_task(
                    selected,
                    profile=profile,
                    day=day,
                    weak_modules=weak_modules,
                    scheduled_ids=day_start_completed,
                    start_day=start_day,
                )
                day_tasks.append(planned)
                flat_tasks.append(planned)
                scheduled_ids.add(selected.task_id)
                minutes_left -= selected.estimated_minutes

            future_days.append(
                DailyPlan(
                    day=day,
                    tasks=day_tasks,
                    total_minutes=profile.daily_study_minutes - minutes_left,
                    remaining_minutes=minutes_left,
                    total_value=round(sum(task.base_value for task in day_tasks), 2),
                )
            )

        historical_daily = [self._dict_to_daily_plan(day) for day in historical_plan]
        full_plan = historical_daily + future_days
        full_tasks = [task for day in full_plan for task in day.tasks]
        unplanned = [
            task_id
            for task_id, task in all_tasks.items()
            if task_id not in scheduled_ids and task_id not in completed_task_ids
        ]
        result = PlannerResult(
            user_profile=profile.to_dict(),
            plan=full_plan,
            tasks=full_tasks,
            summary=self._summary(profile, full_plan, completed_task_ids, unplanned),
            planner_metadata={
                "algorithm": "Adaptive Unlock-aware Mastery-guided Planner",
                "event": event,
                "mastery_threshold": profile.mastery_threshold,
                "completed_task_ids": sorted(completed_task_ids),
                "blocked_task_ids": sorted(blocked_task_ids),
                "mastery_scores": mastery_scores,
                "unplanned_task_ids": unplanned,
                "weights": {
                    "unlock_weight": self.unlock_weight,
                    "weak_module_bonus": self.weak_module_bonus,
                    "review_bonus": self.review_bonus,
                    "urgency_weight": self.urgency_weight,
                    "difficulty_weight": self.difficulty_weight,
                    "time_cost_weight": self.time_cost_weight,
                },
            },
        )
        return result.to_dict()

    def _priority_score(
        self,
        task: TaskNode,
        profile: UserProfile,
        weak_modules: set[str],
        day: int,
        start_day: int,
    ) -> float:
        weak_bonus = self.weak_module_bonus if task.module.lower() in weak_modules else 0.0
        review_bonus = self.review_bonus if task.is_review else 0.0
        days_left = max(profile.prep_days - day + 1, 1)
        urgency_bonus = self.urgency_weight / days_left
        unlock_score = self._unlock_score(task)
        difficulty_penalty = task.difficulty * self.difficulty_weight
        time_penalty = task.estimated_minutes * self.time_cost_weight
        early_review_bonus = 4.0 if task.is_review and day == start_day else 0.0
        return round(
            task.base_value
            + weak_bonus
            + review_bonus
            + self.unlock_weight * unlock_score
            + urgency_bonus
            + early_review_bonus
            - difficulty_penalty
            - time_penalty,
            4,
        )

    def _to_planned_task(
        self,
        task: TaskNode,
        *,
        profile: UserProfile,
        day: int,
        weak_modules: set[str],
        scheduled_ids: set[str],
        start_day: int,
    ) -> PlannedTask:
        unlock_score = self._unlock_score(task)
        priority = self._priority_score(task, profile, weak_modules, day, start_day)
        return PlannedTask(
            task_id=task.task_id,
            title=task.title,
            module=task.module,
            estimated_minutes=task.estimated_minutes,
            difficulty=task.difficulty,
            base_value=task.base_value,
            day=day,
            reason=self._reason(task, weak_modules, unlock_score),
            dependency_status=self._dependency_status(task, scheduled_ids),
            unlock_score=round(unlock_score, 2),
            mastery_status="review_required" if task.is_review else "planned",
            resource_query=task.to_dict()["resource_query"],
            priority_score=priority,
            is_review=task.is_review,
            review_of=task.review_of,
        )

    def _reason(self, task: TaskNode, weak_modules: set[str], unlock_score: float) -> str:
        reasons: list[str] = []
        if task.is_review:
            reasons.append(f"review task for insufficient mastery of {task.review_of}")
        if task.module.lower() in weak_modules:
            reasons.append("matches a weak module")
        if unlock_score >= 30:
            reasons.append("unlocks multiple high-value downstream tasks")
        if not reasons:
            reasons.append("high value under the remaining time budget")
        return "; ".join(reasons)

    def _is_available(
        self,
        task: TaskNode,
        completed_before_day: set[str],
        blocked_task_ids: set[str],
    ) -> bool:
        if task.is_review:
            return bool(task.review_of and task.review_of not in completed_before_day)
        if task.task_id in blocked_task_ids:
            return False
        return all(prereq in completed_before_day for prereq in task.prerequisites)

    def _dependency_status(self, task: TaskNode, scheduled_ids: set[str]) -> str:
        if task.is_review:
            return f"review generated for {task.review_of}"
        if not task.prerequisites:
            return "no prerequisites"
        missing = [prereq for prereq in task.prerequisites if prereq not in scheduled_ids]
        if missing:
            return f"blocked by {', '.join(missing)}"
        return "all prerequisites satisfied before this day"

    def _make_review_task(self, task_id: str, earliest_day: int, mastery_score: int) -> TaskNode:
        original = self.tasks[task_id]
        minutes = max(20, int(round(original.estimated_minutes * 0.5 / 5) * 5))
        return TaskNode(
            task_id=f"review__{task_id}__day{earliest_day}",
            title=f"Review: {original.title}",
            module=original.module,
            estimated_minutes=minutes,
            base_value=max(original.base_value * 0.7, 25),
            difficulty=max(original.difficulty - 0.5, 1),
            prerequisites=[],
            exam=original.exam,
            resource_query=f"{original.exam} targeted review for {original.title} after mastery score {mastery_score}",
            tags=[*original.tags, "review"],
            is_review=True,
            review_of=task_id,
        )

    def _unlock_score(self, task: TaskNode) -> float:
        if task.is_review and task.review_of:
            return self.unlock_scores.get(task.review_of, 0.0)
        return self.unlock_scores.get(task.task_id, 0.0)

    def _compute_unlock_scores(self) -> dict[str, float]:
        scores: dict[str, float] = {}
        for task_id in self.tasks:
            score = 0.0
            queue: deque[tuple[str, int]] = deque((child, 1) for child in self.children[task_id])
            seen: set[str] = set()
            while queue:
                child_id, depth = queue.popleft()
                if child_id in seen:
                    continue
                seen.add(child_id)
                child = self.tasks[child_id]
                score += child.base_value / depth
                for grandchild in self.children[child_id]:
                    queue.append((grandchild, depth + 1))
            scores[task_id] = round(score, 2)
        return scores

    def _build_children(self) -> dict[str, list[str]]:
        children: dict[str, list[str]] = defaultdict(list)
        for task in self.tasks.values():
            children.setdefault(task.task_id, [])
            for prereq in task.prerequisites:
                children[prereq].append(task.task_id)
        return dict(children)

    def _validate_graph(self) -> None:
        for task in self.tasks.values():
            for prereq in task.prerequisites:
                if prereq not in self.tasks:
                    raise ValueError(f"Task {task.task_id} references unknown prerequisite {prereq}")

        indegree = {task_id: 0 for task_id in self.tasks}
        for task in self.tasks.values():
            for prereq in task.prerequisites:
                indegree[task.task_id] += 1
        queue = deque(task_id for task_id, degree in indegree.items() if degree == 0)
        visited = 0
        while queue:
            task_id = queue.popleft()
            visited += 1
            for child in self.children[task_id]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if visited != len(self.tasks):
            raise ValueError("Task graph must be a DAG; a cycle was detected")

    def _tasks_for_exam(self, exam: str) -> dict[str, TaskNode]:
        return {task_id: task for task_id, task in self.tasks.items() if task.exam.upper() == exam}

    def _coerce_user_profile(self, value: UserProfile | dict[str, Any]) -> UserProfile:
        if isinstance(value, UserProfile):
            return value
        return UserProfile(**value)

    def _coerce_feedback(self, value: TaskFeedback | dict[str, Any]) -> TaskFeedback:
        if isinstance(value, TaskFeedback):
            return value
        return TaskFeedback(**value)

    def _lookup_planned_or_base_task(self, existing_plan: dict[str, Any], task_id: str) -> TaskNode:
        for task in existing_plan.get("tasks", []):
            if task["task_id"] == task_id:
                return TaskNode(
                    task_id=task["task_id"],
                    title=task["title"],
                    module=task["module"],
                    estimated_minutes=task["estimated_minutes"],
                    base_value=task["base_value"],
                    difficulty=task["difficulty"],
                    prerequisites=[],
                    exam=existing_plan.get("user_profile", {}).get("target_exam", "IELTS"),
                    resource_query=task.get("resource_query"),
                    is_review=task.get("is_review", False),
                    review_of=task.get("review_of"),
                )
        if task_id not in self.tasks:
            raise KeyError(f"Unknown feedback task_id: {task_id}")
        return self.tasks[task_id]

    def _historical_days(self, existing_plan: dict[str, Any], current_day: int) -> list[dict[str, Any]]:
        return [day for day in existing_plan.get("plan", []) if day["day"] <= current_day]

    def _load_pending_reviews(self, existing_plan: dict[str, Any], current_day: int) -> list[TaskNode]:
        reviews: list[TaskNode] = []
        for task in existing_plan.get("tasks", []):
            if not task.get("is_review") or task.get("day", 0) <= current_day:
                continue
            reviews.append(
                TaskNode(
                    task_id=task["task_id"],
                    title=task["title"],
                    module=task["module"],
                    estimated_minutes=task["estimated_minutes"],
                    base_value=task["base_value"],
                    difficulty=task["difficulty"],
                    exam=existing_plan.get("user_profile", {}).get("target_exam", "IELTS"),
                    resource_query=task["resource_query"],
                    is_review=True,
                    review_of=task.get("review_of"),
                )
            )
        return reviews

    def _dedupe_reviews(self, review_tasks: list[TaskNode], completed_task_ids: set[str]) -> list[TaskNode]:
        deduped: dict[str, TaskNode] = {}
        for review in review_tasks:
            if not review.review_of or review.review_of in completed_task_ids:
                continue
            deduped[review.review_of] = review
        return list(deduped.values())

    def _dict_to_daily_plan(self, day: dict[str, Any]) -> DailyPlan:
        tasks = [PlannedTask(**task) for task in day.get("tasks", [])]
        return DailyPlan(
            day=day["day"],
            tasks=tasks,
            total_minutes=day.get("total_minutes", sum(task.estimated_minutes for task in tasks)),
            remaining_minutes=day.get("remaining_minutes", 0),
            total_value=day.get("total_value", round(sum(task.base_value for task in tasks), 2)),
        )

    def _summary(
        self,
        profile: UserProfile,
        plan: list[DailyPlan],
        completed_task_ids: set[str],
        unplanned: list[str],
    ) -> dict[str, Any]:
        planned_tasks = [task for day in plan for task in day.tasks]
        minutes = sum(day.total_minutes for day in plan)
        value = round(sum(task.base_value for task in planned_tasks), 2)
        modules: dict[str, int] = defaultdict(int)
        for task in planned_tasks:
            modules[task.module] += task.estimated_minutes
        return {
            "total_days": profile.prep_days,
            "planned_task_count": len(planned_tasks),
            "completed_task_count": len(completed_task_ids),
            "total_planned_minutes": minutes,
            "total_learning_value": value,
            "minutes_by_module": dict(sorted(modules.items())),
            "unplanned_task_count": len(unplanned),
        }
