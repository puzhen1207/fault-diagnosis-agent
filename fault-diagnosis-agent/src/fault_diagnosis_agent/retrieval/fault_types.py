from __future__ import annotations


FAULT_TYPE_MAP: dict[str, list[str]] = {
    "compressor_overpressure": ["压缩机压力过高", "压缩机超压", "出口压力高", "压缩机压力高"],
    "compressor_underpressure": ["压缩机压力过低", "压缩机低压", "出口压力低"],
    "separator_high_level": ["分离器液面过高", "分离器液位高", "分离器高液位", "带液"],
    "pipeline_overpressure": ["干管压力过高", "干线压力高", "干管超压"],
    "pipeline_underpressure": ["干管压力过低", "干线压力低", "干管低压"],
    "station_export_overpressure": ["集气站外输压力过高", "外输压力高", "外输超压"],
    "station_export_underpressure": ["集气站外输压力过低", "外输压力低"],
    "well_liquid_loading": ["气井积液", "携液能力不足", "油套压差大", "井筒积液"],
    "well_low_productivity": ["气井产能不足", "产量低", "气量低", "产能下降"],
}

FAULT_LABELS: dict[str, str] = {
    "compressor_overpressure": "压缩机压力过高",
    "compressor_underpressure": "压缩机压力过低",
    "separator_high_level": "分离器液面过高",
    "pipeline_overpressure": "干管压力过高",
    "pipeline_underpressure": "干管压力过低",
    "station_export_overpressure": "集气站外输压力过高",
    "station_export_underpressure": "集气站外输压力过低",
    "well_liquid_loading": "气井积液",
    "well_low_productivity": "气井产能不足",
}


def classify_fault_type(query: str) -> str:
    normalized = query.lower()
    best_type = "unknown"
    best_score = 0
    for fault_type, aliases in FAULT_TYPE_MAP.items():
        score = 0
        for alias in aliases:
            if alias.lower() in normalized:
                score += len(alias)
        if score > best_score:
            best_type = fault_type
            best_score = score
    if best_type != "unknown":
        return best_type

    high_words = ("过高", "超压", "高", "升高")
    low_words = ("过低", "低压", "低", "下降")
    if "压缩机" in query and "压力" in query:
        if any(word in query for word in low_words) or "入口压力低" in query:
            return "compressor_underpressure"
        if any(word in query for word in high_words) or "MPa" in query or "报警" in query:
            return "compressor_overpressure"
    if "分离器" in query and any(word in query for word in ("液位", "液面")):
        if any(word in query for word in high_words) or "报警" in query:
            return "separator_high_level"
    if any(word in query for word in ("干管", "干线")) and "压力" in query:
        if any(word in query for word in low_words):
            return "pipeline_underpressure"
        if any(word in query for word in high_words):
            return "pipeline_overpressure"
    if "外输" in query and "压力" in query:
        if any(word in query for word in low_words):
            return "station_export_underpressure"
        if any(word in query for word in high_words):
            return "station_export_overpressure"
    return best_type
