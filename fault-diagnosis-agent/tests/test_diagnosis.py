from fault_diagnosis_agent.diagnosis import run_diagnosis


def test_compressor_overpressure_diagnosis():
    result = run_diagnosis("压缩机压力过高报警怎么办？")
    assert result["fault_type"] == "compressor_overpressure"
    assert result["solution_steps"]
    assert "压缩机" in result["final_answer"]


def test_missing_info_route():
    result = run_diagnosis("现在报警了，怎么办？")
    assert result["need_more_info"] is True
    assert "请明确" in result["final_answer"]

