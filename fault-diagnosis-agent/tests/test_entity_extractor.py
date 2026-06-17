from fault_diagnosis_agent.retrieval.entity_extractor import FaultEntityExtractor


def test_extract_threshold_and_device():
    result = FaultEntityExtractor().extract("压缩机压力4.5MPa过高报警")
    assert result["device"] == "压缩机"
    assert result["indicator"] == "压力"
    assert result["threshold"] == "4.5MPa"

