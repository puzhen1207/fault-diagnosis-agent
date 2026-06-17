from __future__ import annotations

from fault_diagnosis_agent.models import FaultClassificationTrace, FaultTypeCandidate

# 关键: 每个 fault_type 的匹配关键词（按优先级）
# score = 匹配到的关键词总长度，越长越精确
FAULT_TYPE_MAP: dict[str, list[str]] = {
    "compressor_pressure_high": [
        "压缩机压力过高", "压缩机超压", "一排压力高高限", "二排压力高高限",
        "一排压力高", "二排压力高", "进气压力高高限", "进气压力高",
        "出口压力高", "排气压力高", "压缩机压力高", "压缩机压力高报警",
    ],
    "compressor_pressure_low": [
        "压缩机压力过低", "入口压力低", "进气压力低低限", "进气压力低",
        "一排压力低", "二排压力低", "一排压力低低限", "二排压力低低限",
        "压缩机低压", "出口压力低",
    ],
    "separator_level_high": [
        "分离器液位过高", "分离器高液位", "液位高高限", "液位高限",
        "分离器带液", "分离器液位高",
    ],
    "separator_level_low": [
        "分离器液位过低", "分离器低液位", "液位低低限", "液位低限",
    ],
    "separator_pressure_high": [
        "分离器进口压力过高", "分离器进口压力高", "分离器压力高",
        "进口压力高高限", "进口压力高限",
    ],
    "compressor_speed_high": [
        "压缩机转速高", "转速高高限", "转速高限", "压缩机转速过高",
        "压缩机超速",
    ],
    "compressor_speed_low": [
        "压缩机转速低", "转速低低限", "转速低限", "压缩机转速过低",
        "转速下降",
    ],
    "pipeline_pressure_high": [
        "干管压力过高", "干线压力高", "干管超压",
    ],
    "pipeline_pressure_low": [
        "干管压力过低", "干线压力低", "干管低压",
    ],
    "station_export_pressure": [
        "集气站外输压力过高", "外输压力高", "外输超压",
        "集气站外输压力过低", "外输压力低",
    ],
    "well_liquid_loading": [
        "气井积液", "井筒积液", "携液能力不足", "油套压差大",
        "气井产能不足", "气井产量低", "气量低", "产能下降",
    ],
}

FAULT_LABELS: dict[str, str] = {
    "compressor_pressure_high": "压缩机压力过高",
    "compressor_pressure_low": "压缩机压力过低",
    "separator_level_high": "分离器液位过高",
    "separator_level_low": "分离器液位过低",
    "separator_pressure_high": "分离器进口压力过高",
    "compressor_speed_high": "压缩机转速过高",
    "compressor_speed_low": "压缩机转速过低",
    "pipeline_pressure_high": "干管压力过高",
    "pipeline_pressure_low": "干管压力过低",
    "station_export_pressure": "集气站外输压力异常",
    "well_liquid_loading": "气井积液与产能异常",
}


def classify_fault_type_with_trace(query: str) -> tuple[str, FaultClassificationTrace]:
    """带追踪的故障类型分类。返回 (最终选中类型, 分类轨迹对象)。

    对所有 11 个故障类型进行关键词打分，若精确匹配未命中，则使用启发式
    fallback 规则（例如仅包含 "压缩机" + "压力" + "高" 等关键词组合）。
    """
    normalized = query.lower()
    all_candidates: list[FaultTypeCandidate] = []
    best_type = "unknown"
    best_score = 0.0
    heuristic_applied = False

    # 第 1 步：对所有 11 个类型按关键词打分
    for fault_type, keywords in FAULT_TYPE_MAP.items():
        matched: list[str] = []
        score = 0.0
        for keyword in keywords:
            if keyword.lower() in normalized:
                matched.append(keyword)
                score += float(len(keyword))  # 长关键词权重更高
        candidate = FaultTypeCandidate(
            fault_type=fault_type,
            label=FAULT_LABELS.get(fault_type, fault_type),
            matched_keywords=matched,
            keyword_score=score,
            heuristic_applied=False,
        )
        all_candidates.append(candidate)
        if score > best_score:
            best_score = score
            best_type = fault_type

    # 第 2 步：Fallback 启发式规则（当精确匹配未命中时）
    if best_type == "unknown":
        heuristic_applied = True
        if "压缩机" in query and "压力" in query:
            if any(w in query for w in ["过高", "超压", "高", "报警", "高限"]):
                best_type = "compressor_pressure_high"
            elif any(w in query for w in ["过低", "低压", "低", "不足"]):
                best_type = "compressor_pressure_low"
            else:
                best_type = "compressor_pressure_high"
        elif "分离器" in query and "液位" in query:
            if any(w in query for w in ["过高", "高", "高高"]):
                best_type = "separator_level_high"
            elif any(w in query for w in ["过低", "低", "低低"]):
                best_type = "separator_level_low"
            else:
                best_type = "separator_level_high"
        elif "分离器" in query and "压力" in query:
            if any(w in query for w in ["过高", "高", "进口"]):
                best_type = "separator_pressure_high"
        elif "压缩机" in query and "转速" in query:
            if any(w in query for w in ["过高", "高", "超速"]):
                best_type = "compressor_speed_high"
            elif any(w in query for w in ["过低", "低", "下降"]):
                best_type = "compressor_speed_low"
            else:
                best_type = "compressor_speed_high"
        elif "干管" in query and "压力" in query:
            if any(w in query for w in ["过高", "高"]):
                best_type = "pipeline_pressure_high"
            elif any(w in query for w in ["过低", "低"]):
                best_type = "pipeline_pressure_low"
        elif "外输" in query:
            best_type = "station_export_pressure"
        elif "气井" in query and any(w in query for w in ["积液", "压差", "产能", "产量", "气量"]):
            best_type = "well_liquid_loading"

        # 更新命中候选的 heuristic 标记，便于可视化
        for cand in all_candidates:
            if cand.fault_type == best_type:
                cand.heuristic_applied = True

    # 所有候选按得分降序，得到 top candidates
    ranked_candidates = sorted(all_candidates, key=lambda c: c.keyword_score, reverse=True)

    trace = FaultClassificationTrace(
        normalized=query,
        candidates=ranked_candidates[:5],  # top 5
        fallback_applied=heuristic_applied,
        all_candidates=all_candidates,
        selected_fault_type=best_type,
        heuristic_applied=heuristic_applied,
    )
    return best_type, trace


def classify_fault_type(query: str) -> str:
    """基于关键词匹配的故障分类（向后兼容：仅返回故障类型 key）。"""
    fault_type, _ = classify_fault_type_with_trace(query)
    return fault_type
