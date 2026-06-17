from __future__ import annotations

import re


class FaultEntityExtractor:
    """Extract device, indicator, condition and threshold from a Chinese fault query."""

    def extract(self, query: str) -> dict[str, str | None]:
        result: dict[str, str | None] = {
            "device": None,
            "indicator": None,
            "condition": None,
            "threshold": None,
        }

        patterns = {
            "device": r"(压缩机|分离器|干管|干线|集气站|气井|油管|套管|外输)",
            "indicator": r"(压力|液位|液面|温度|气量|产量|压差)",
            "condition": r"(过高|过低|异常|超压|低压|高液位|积液|不足|不稳定|下降|升高)",
            "threshold": r"(\d+(?:\.\d+)?)\s*(MPa|kPa|方|米|%)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                result[key] = "".join(match.groups()) if key == "threshold" else match.group(1)

        if result["device"] == "外输":
            result["device"] = "集气站外输"
        if result["device"] == "干线":
            result["device"] = "干管"
        if result["condition"] == "超压":
            result["condition"] = "过高"
        if result["condition"] == "低压":
            result["condition"] = "过低"
        return result

