from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskNode:
    task_id: str
    title: str
    module: str
    estimated_minutes: int
    base_value: float
    difficulty: float
    prerequisites: list[str] = field(default_factory=list)
    exam: str = "IELTS"
    resource_query: str | None = None
    tags: list[str] = field(default_factory=list)
    is_review: bool = False
    review_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["resource_query"] is None:
            data["resource_query"] = f"{self.exam} {self.title} {self.module} explanation practice feedback"
        return data


@dataclass(frozen=True)
class UserProfile:
    prep_days: int
    daily_study_minutes: int
    target_exam: str
    weak_modules: list[str] = field(default_factory=list)
    current_level: str = "intermediate"
    mastery_threshold: int = 70
    completed_task_ids: list[str] = field(default_factory=list)
    mastery_scores: dict[str, int] = field(default_factory=dict)

    def normalized_exam(self) -> str:
        return self.target_exam.strip().upper()

    def normalized_weak_modules(self) -> set[str]:
        return {module.strip().lower() for module in self.weak_modules}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskFeedback:
    task_id: str
    mastery_score: int
    completed: bool = True
    minutes_spent: int | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlannedTask:
    task_id: str
    title: str
    module: str
    estimated_minutes: int
    difficulty: float
    base_value: float
    day: int
    reason: str
    dependency_status: str
    unlock_score: float
    mastery_status: str
    resource_query: str
    priority_score: float
    is_review: bool = False
    review_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyPlan:
    day: int
    tasks: list[PlannedTask]
    total_minutes: int
    remaining_minutes: int
    total_value: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tasks"] = [task.to_dict() for task in self.tasks]
        return data


@dataclass(frozen=True)
class PlannerResult:
    user_profile: dict[str, Any]
    plan: list[DailyPlan]
    tasks: list[PlannedTask]
    summary: dict[str, Any]
    planner_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_profile": self.user_profile,
            "plan": [day.to_dict() for day in self.plan],
            "tasks": [task.to_dict() for task in self.tasks],
            "summary": self.summary,
            "planner_metadata": self.planner_metadata,
        }
