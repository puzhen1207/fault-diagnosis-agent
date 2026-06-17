from __future__ import annotations

import re

from fault_diagnosis_agent.models import EntityExtractionTrace


class FaultEntityExtractor:
    """基于规则的实体提取器。识别设备、指标、状态/条件与阈值四个槽位。"""

    # ---- 设备识别规则 --------------------------------------------------------
    DEVICE_PATTERNS = [
        (r"压缩机", "压缩机"),
        (r"分离器", "分离器"),
        (r"干管|干线", "干管"),
        (r"集气站|外输", "集气站外输"),
        (r"气井|井口", "气井"),
    ]

    # ---- 指标识别规则 --------------------------------------------------------
    INDICATOR_PATTERNS = [
        (r"液位|液面", "液位"),
        (r"压力", "压力"),
        (r"温度", "温度"),
        (r"转速", "转速"),
        (r"压差", "压差"),
        (r"产量|气量", "产量"),
    ]

    # ---- 状态/条件识别（增强版） ---------------------------------------------
    HIGH_PATTERNS = ["过高", "超压", "高高", "高限", "高报警", "压力高", "液位高"]
    LOW_PATTERNS = ["过低", "低压", "低低", "低限", "低报警", "压力低", "液位低"]
    ABNORMAL_PATTERNS = ["异常", "故障", "报警", "堵塞", "冻堵", "刺漏", "积液", "不足", "下降"]

    # ---- 阈值识别（如 "3.7兆帕" 或 "3.7MPa"） --------------------------------
    THRESHOLD_PATTERN = r"(\d+(?:\.\d+)?)\s*(MPa|兆帕|kPa|kpa|方|米|%)"

    def extract(self, query: str) -> dict[str, str | None]:
        """向后兼容：仅返回字典形式的提取结果。"""
        return self.extract_with_trace(query).result

    def extract_with_trace(self, query: str) -> EntityExtractionTrace:
        """带追踪的实体提取：返回每个槽位命中的原文片段与最终结果。"""
        result: dict[str, str | None] = {
            "device": None,
            "indicator": None,
            "condition": None,
            "threshold": None,
        }
        device_match: str | None = None
        indicator_match: str | None = None
        condition_match: str | None = None
        threshold_match: str | None = None

        # 设备识别（返回首个命中的原文片段）
        for pattern, value in self.DEVICE_PATTERNS:
            hit = re.search(pattern, query)
            if hit:
                result["device"] = value
                device_match = hit.group(0)
                break

        # 指标识别
        for pattern, value in self.INDICATOR_PATTERNS:
            hit = re.search(pattern, query)
            if hit:
                result["indicator"] = value
                indicator_match = hit.group(0)
                break

        # 状态/条件识别
        condition = None
        for p in self.HIGH_PATTERNS:
            if p in query:
                condition = "过高"
                condition_match = p
                break
        if condition is None:
            for p in self.LOW_PATTERNS:
                if p in query:
                    condition = "过低"
                    condition_match = p
                    break
        if condition is None:
            for p in self.ABNORMAL_PATTERNS:
                if p in query:
                    condition = "异常"
                    condition_match = p
                    break
        result["condition"] = condition

        # 阈值识别
        hit = re.search(self.THRESHOLD_PATTERN, query, re.IGNORECASE)
        if hit:
            threshold_match = hit.group(0)
            result["threshold"] = threshold_match

        return EntityExtractionTrace(
            raw_query=query,
            device_match=device_match,
            indicator_match=indicator_match,
            condition_match=condition_match,
            threshold_match=threshold_match,
            result=result,
        )
