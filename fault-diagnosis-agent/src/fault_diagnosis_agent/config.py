from __future__ import annotations

import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.kb_path = Path(os.getenv("FAULT_KB_PATH", "data/processed/fault_knowledge.json"))
        self.feedback_path = Path(os.getenv("FAULT_FEEDBACK_PATH", "data/feedback/feedback.jsonl"))


settings = Settings()

