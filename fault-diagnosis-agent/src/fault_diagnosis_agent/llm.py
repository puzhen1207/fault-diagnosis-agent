from __future__ import annotations

from typing import Any, Dict, Optional

from fault_diagnosis_agent.config import settings


class OptionalLLM:
    """可选 LLM 客户端——兼容所有提供 OpenAI 兼容接口的服务。

    支持的提供商（非穷尽）：
    - OpenAI (默认)
    - DeepSeek (https://api.deepseek.com/v1)
    - 智谱 AI (https://open.bigmodel.cn/api/paas/v4)
    - 月之暗面 Kimi (https://api.moonshot.cn/v1)
    - 通义千问 DashScope (https://dashscope.aliyuncs.com/compatible-mode/v1)
    - 百度千帆 (https://qianfan.baidubce.com/v2)
    - Ollama (http://localhost:11434/v1, API_KEY 随意填写非空字符串)
    - vLLM / LM Studio / 其他本地部署的 OpenAI 兼容服务

    若未配置 API Key，则 fallback 至本地规则推理，不影响核心流程。
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._provider: str = "openai"  # 仅用于日志/调试
        if not settings.llm_api_key:
            return
        try:
            from langchain_openai import ChatOpenAI

            # 构造 ChatOpenAI 的可选 kwargs：只在显式设置 base_url 时传入
            chat_kwargs: Dict[str, Any] = {
                "model": settings.llm_model,
                "temperature": 0,
                "api_key": settings.llm_api_key,
            }
            if settings.llm_base_url:
                chat_kwargs["base_url"] = settings.llm_base_url
                self._provider = settings.llm_base_url

            self._client = ChatOpenAI(**chat_kwargs)
        except Exception:
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def provider(self) -> str:
        return self._provider

    def invoke(self, prompt: str, system: Optional[str] = None) -> str:
        """调用 LLM 返回文本内容。

        Args:
            prompt: 用户/任务提示词。
            system: 可选的 system 提示词（不保证所有模型都支持；传入时会自动包装为 messages）。
        """
        if not self._client:
            raise RuntimeError("LLM is not configured.")
        try:
            if system is not None:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ]
                return self._client.invoke(messages).content.strip()
            return self._client.invoke(prompt).content.strip()
        except Exception as exc:
            raise RuntimeError(f"LLM call failed: {exc}") from exc


optional_llm = OptionalLLM()
