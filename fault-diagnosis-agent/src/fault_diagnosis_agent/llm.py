from __future__ import annotations

from fault_diagnosis_agent.config import settings


class OptionalLLM:
    def __init__(self) -> None:
        self._client = None
        if settings.openai_api_key:
            try:
                from langchain_openai import ChatOpenAI

                self._client = ChatOpenAI(model=settings.openai_model, temperature=0)
            except Exception:
                self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def invoke(self, prompt: str) -> str:
        if not self._client:
            raise RuntimeError("LLM is not configured.")
        return self._client.invoke(prompt).content.strip()


optional_llm = OptionalLLM()

