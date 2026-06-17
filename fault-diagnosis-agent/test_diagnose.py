import json
import urllib.request

# 本地测试
from fault_diagnosis_agent.diagnosis import run_diagnosis
from fault_diagnosis_agent.retrieval.fault_types import classify_fault_type

print("=== 本地 Python 测试 ===")
queries = [
    "压缩机压力过高报警怎么办？",
    "分离器液位高报警怎么办？",
    "压缩机一排压力过高怎么办？",
    "分离器进口压力高怎么办？",
    "压缩机转速高怎么办？",
    "气井积液怎么办？",
    "干管压力过高报警怎么办？",
    "分离器液位低报警怎么办？",
]
for q in queries:
    ft = classify_fault_type(q)
    state = run_diagnosis(q)
    rc = state.get("root_cause", "")
    if rc and len(rc) > 80:
        rc = rc[:80]
    print("  classify=" + str(ft) + " | fault_type=" + str(state.get("fault_type")) + " | steps=" + str(len(state.get("solution_steps", []))))

print()
print("=== HTTP POST 测试 ===")
for q in queries:
    data = json.dumps({"query": q, "session_id": "http-test"}).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/diagnose",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
        ft = resp.get("fault_type")
        sc = len(resp.get("steps", []))
        rc = resp.get("root_cause", "")
        if rc and len(rc) > 80:
            rc = rc[:80]
        print("  fault_type=" + str(ft) + " | steps=" + str(sc))
    except Exception as e:
        print("  错误: " + str(e))

print()
print("=== 健康检查 ===")
req = urllib.request.Request("http://localhost:8000/health")
resp = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
print("  status: " + str(resp.get("status")))
print("  kb: " + str(resp.get("knowledge_base")))

print()
print("=== 故障类型列表 ===")
req = urllib.request.Request("http://localhost:8000/fault-types")
resp = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
for ft, label in resp.items():
    print("  " + ft + " -> " + label)
