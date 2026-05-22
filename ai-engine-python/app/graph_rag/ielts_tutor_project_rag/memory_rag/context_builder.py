"""Build planner and tutor contexts from retrieved memories."""

from __future__ import annotations

from .mastery_tracker import MasteryTracker


class MemoryContextBuilder:
    def __init__(self, mastery_tracker: MasteryTracker | None = None):
        self.mastery_tracker = mastery_tracker or MasteryTracker()

    def build_context(self, memories: list[dict]) -> str:
        profile = self._first_of_type(memories, "user_profile")
        weak_modules = self._unique(
            memory.get("module")
            for memory in memories
            if memory.get("memory_type") in {"weakness", "task_feedback", "essay_feedback", "speaking_feedback"}
            and memory.get("module")
        )
        weak_skills = self._collect_weak_skills(memories)
        low_score_tasks = self._low_score_tasks(memories)
        preferences = self._collect_preferences(memories)

        lines = ["User Learning Memory:"]
        if profile:
            if profile.get("exam"):
                lines.append(f"- Target exam: {profile['exam']}")
            metadata = profile.get("metadata", {})
            if metadata.get("target_score"):
                lines.append(f"- Target score: {metadata['target_score']}")
            if metadata.get("current_level"):
                lines.append(f"- Current level: {metadata['current_level']}")

        for module in weak_modules:
            lines.append(f"- Weak module: {module}")

        for task in low_score_tasks:
            task_id = task.get("task_id") or "unknown task"
            module = task.get("module") or "unknown module"
            score = task.get("score")
            lines.append(f"- Recent low-score task: {task_id} {module}, score {score}")

        for skill in weak_skills:
            lines.append(f"- Main weakness: {skill}")

        for preference in preferences:
            lines.append(f"- User prefers {preference}")

        if len(lines) == 1:
            lines.append("- No relevant learning memories were retrieved.")
        return "\n".join(lines)

    def build_planner_context(self, memories: list[dict]) -> dict:
        low_score_tasks = self._low_score_tasks(memories)
        completed_tasks = self._unique(
            memory.get("task_id")
            for memory in memories
            if memory.get("task_id") and memory.get("memory_type") in {"task_feedback", "essay_feedback", "speaking_feedback"}
        )

        context = {
            "weak_modules": self._unique(
                memory.get("module")
                for memory in memories
                if memory.get("module")
                and memory.get("memory_type") in {"weakness", "task_feedback", "essay_feedback", "speaking_feedback"}
            ),
            "weak_skills": self._collect_weak_skills(memories),
            "completed_tasks": completed_tasks,
            "low_score_tasks": self._unique(task.get("task_id") for task in low_score_tasks if task.get("task_id")),
            "unfinished_tasks": self._unique(
                memory.get("task_id")
                for memory in memories
                if memory.get("memory_type") == "unfinished_task" and memory.get("task_id")
            ),
            "preferences": self._collect_preferences(memories),
            "recent_scores": {
                memory["task_id"]: memory.get("score")
                for memory in memories
                if memory.get("task_id") and memory.get("score") is not None
            },
            "recommended_tasks": self._unique(
                task
                for memory in memories
                if memory.get("memory_type") == "planner_result"
                for task in memory.get("metadata", {}).get("recommended_tasks", [])
            ),
            "mastery_scores": self.mastery_tracker.build_mastery_state(memories),
            "retrieved_memory_ids": [memory.get("memory_id") for memory in memories if memory.get("memory_id")],
        }
        return context

    def build_tutor_context(self, memories: list[dict]) -> str:
        profile = self._first_of_type(memories, "user_profile")
        exam = (profile or {}).get("exam") or self._first_value(memories, "exam") or "IELTS / TOEFL"
        weak_modules = self._unique(memory.get("module") for memory in memories if memory.get("module"))
        weak_skills = self._collect_weak_skills(memories)
        low_score_tasks = self._low_score_tasks(memories)
        preferences = self._collect_preferences(memories)
        dialogue = self._first_of_type(memories, "socratic_dialogue")

        sentences = [f"The user is preparing for {exam}."]
        if weak_modules:
            sentences.append(f"{weak_modules[0]} is currently the weakest or most relevant module.")
        if low_score_tasks:
            task = low_score_tasks[0]
            sentences.append(
                f"The user recently scored {task.get('score')} on {task.get('task_id')} and needs targeted review."
            )
        if weak_skills:
            sentences.append(f"Key weak skills include {', '.join(weak_skills)}.")
        if preferences:
            sentences.append(f"The user prefers {', '.join(preferences)}.")
        if dialogue:
            diagnosis = dialogue.get("metadata", {}).get("diagnosis") or dialogue.get("content")
            sentences.append(f"Recent Socratic diagnosis: {diagnosis}")

        sentences.append(
            "When tutoring, avoid directly giving a full model answer. Use Socratic questions to help the user clarify the claim, explain the causal chain, provide concrete evidence, and connect examples back to the thesis."
        )
        return " ".join(sentences)

    def _collect_weak_skills(self, memories: list[dict]) -> list[str]:
        skills = []
        for memory in memories:
            if memory.get("skill"):
                skills.append(memory["skill"])
            for skill in memory.get("metadata", {}).get("weak_skills", []):
                skills.append(skill)
        return self._unique(skills)

    def _collect_preferences(self, memories: list[dict]) -> list[str]:
        preferences = []
        for memory in memories:
            metadata = memory.get("metadata", {})
            preferences.extend(metadata.get("preferences", []))
            if memory.get("memory_type") == "learning_preference":
                preference = metadata.get("preference") or memory.get("content")
                if preference:
                    preferences.append(preference)
        return self._unique(preferences)

    def _low_score_tasks(self, memories: list[dict]) -> list[dict]:
        tasks = []
        seen_task_ids = set()
        for memory in memories:
            if memory.get("task_id") and memory.get("score") is not None and float(memory["score"]) < 65:
                if memory["task_id"] in seen_task_ids:
                    continue
                seen_task_ids.add(memory["task_id"])
                tasks.append(memory)
        return tasks

    def _first_of_type(self, memories: list[dict], memory_type: str) -> dict | None:
        return next((memory for memory in memories if memory.get("memory_type") == memory_type), None)

    def _first_value(self, memories: list[dict], key: str):
        return next((memory.get(key) for memory in memories if memory.get(key)), None)

    def _unique(self, values) -> list:
        result = []
        seen = set()
        for value in values:
            if value is None:
                continue
            marker = str(value)
            if marker not in seen:
                seen.add(marker)
                result.append(value)
        return result
