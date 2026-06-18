from __future__ import annotations

import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        # ---- LLM 配置（兼容任意 OpenAI 兼容 API） ----
        # 说明：开发者可自由切换至 DeepSeek / 智谱 / 月之暗面 / 千问 / Ollama 等任何提供 OpenAI 兼容接口的服务。
        # 优先级：LLM_API_KEY > OPENAI_API_KEY（后者保留用于向后兼容）
        self.llm_api_key = os.getenv("LLM_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        # LLM_BASE_URL: 自定义 API 端点；不设置时使用 OpenAI 官方地址
        self.llm_base_url = os.getenv("LLM_BASE_URL", "") or None
        # LLM_MODEL: 模型名称；不设置时使用 gpt-4o-mini
        self.llm_model = os.getenv("LLM_MODEL", "") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # ---- 知识库与反馈路径 ----
        self.kb_path = Path(os.getenv("FAULT_KB_PATH", "data/processed/fault_knowledge.json"))
        self.feedback_path = Path(os.getenv("FAULT_FEEDBACK_PATH", "data/feedback/feedback.jsonl"))


settings = Settings()
