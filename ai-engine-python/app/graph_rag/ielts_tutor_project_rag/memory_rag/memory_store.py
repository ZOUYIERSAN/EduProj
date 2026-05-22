"""Local JSONL storage for learning memories."""

from __future__ import annotations

import json
from pathlib import Path

from .memory_schema import validate_memory


class JSONLMemoryStore:
    def __init__(self, file_path: str = "data/memory_store.jsonl"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.touch(exist_ok=True)

    def add_memory(self, memory: dict) -> str:
        validate_memory(memory)
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(memory, ensure_ascii=False) + "\n")
        return memory["memory_id"]

    def load_all_memories(self) -> list[dict]:
        memories: list[dict] = []
        if not self.file_path.exists():
            return memories

        with self.file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    memory = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(memory, dict):
                    memories.append(memory)
        return memories

    def get_user_memories(self, user_id: str) -> list[dict]:
        return [memory for memory in self.load_all_memories() if memory.get("user_id") == user_id]

    def clear_store(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text("", encoding="utf-8")
