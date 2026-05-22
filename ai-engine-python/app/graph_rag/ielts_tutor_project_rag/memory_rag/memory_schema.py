"""Schema helpers for user-specific learning memories.

The project intentionally uses plain dictionaries so the module can be
connected later to planners, LLM prompts, or API responses without adapters.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


SUPPORTED_MEMORY_TYPES = {
    "user_profile",
    "task_feedback",
    "weakness",
    "essay_feedback",
    "speaking_feedback",
    "socratic_dialogue",
    "learning_preference",
    "planner_result",
    "unfinished_task",
    "mastery_update",
    "error_pattern",
}

REQUIRED_FIELDS = {
    "memory_id",
    "user_id",
    "timestamp",
    "memory_type",
    "content",
    "importance",
    "metadata",
}


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def create_memory(
    user_id: str,
    memory_type: str,
    content: str,
    exam: str | None = None,
    module: str | None = None,
    skill: str | None = None,
    task_id: str | None = None,
    score: float | int | None = None,
    importance: float = 0.5,
    metadata: dict | None = None,
    memory_id: str | None = None,
    timestamp: str | None = None,
) -> dict:
    """Create a validated memory dictionary.

    Optional fields are kept in the dictionary with ``None`` values because
    downstream components often benefit from a stable shape.
    """
    memory = {
        "memory_id": memory_id or f"m_{uuid4().hex[:12]}",
        "user_id": user_id,
        "timestamp": timestamp or _utc_timestamp(),
        "memory_type": memory_type,
        "exam": exam,
        "module": module,
        "skill": skill,
        "task_id": task_id,
        "content": content,
        "score": score,
        "importance": float(importance),
        "metadata": metadata or {},
    }
    validate_memory(memory)
    return memory


def validate_memory(memory: dict) -> bool:
    """Validate required fields and basic value ranges.

    Returns True when valid and raises ValueError with a useful message when
    invalid. Keeping validation explicit makes storage failures easier to debug.
    """
    missing = [field for field in REQUIRED_FIELDS if field not in memory]
    if missing:
        raise ValueError(f"Memory is missing required fields: {', '.join(missing)}")

    if not isinstance(memory["user_id"], str) or not memory["user_id"].strip():
        raise ValueError("Memory field 'user_id' must be a non-empty string.")

    if memory["memory_type"] not in SUPPORTED_MEMORY_TYPES:
        supported = ", ".join(sorted(SUPPORTED_MEMORY_TYPES))
        raise ValueError(f"Unsupported memory_type '{memory['memory_type']}'. Supported: {supported}")

    if not isinstance(memory["content"], str) or not memory["content"].strip():
        raise ValueError("Memory field 'content' must be a non-empty string.")

    try:
        importance = float(memory["importance"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Memory field 'importance' must be numeric.") from exc

    if not 0 <= importance <= 1:
        raise ValueError("Memory field 'importance' must be between 0 and 1.")

    if not isinstance(memory["metadata"], dict):
        raise ValueError("Memory field 'metadata' must be a dictionary.")

    if memory.get("score") is not None:
        try:
            float(memory["score"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Memory field 'score' must be numeric when provided.") from exc

    return True
