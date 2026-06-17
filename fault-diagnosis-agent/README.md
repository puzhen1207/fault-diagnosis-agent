# 油气田故障诊断智能问答 Agent

这是一个基于 FastAPI + LangGraph 的油气田设备故障诊断 RAG Agent 工程。它面向压缩机、分离器、干管、集气站外输和气井积液等场景，支持自然语言故障描述、实体抽取、故障分类、知识库检索、根因分析、处置步骤生成和反馈收集。

## 功能

- `/diagnose`：输入故障描述，返回根因分析、处置步骤、风险提示和参考依据。
- `/feedback`：记录用户对诊断答案的评分和意见。
- Word 知识库导入：支持将《知识.docx》解析为结构化 JSON。
- LangGraph 状态机：分类 -> 信息补全判断 -> 检索 -> 根因分析 -> 方案生成 -> 最终回答。
- 可选 LLM：未配置 API Key 时也能用本地规则和知识库跑通；配置后可增强根因分析。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

测试诊断：

```bash
curl -X POST http://127.0.0.1:8000/diagnose ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"压缩机压力过高报警怎么办？\",\"session_id\":\"test123\"}"
```

## 导入真实 Word 知识库

将你的 `知识.docx` 放入 `data/raw/` 后执行：

```bash
python scripts/build_knowledge_base.py --doc data/raw/知识.docx --output data/processed/fault_knowledge.json
```

脚本会按标题和步骤抽取知识块，并写入 API 默认读取的知识库文件。

## 评估

内置了 20 条故障场景测试用例：

```bash
python scripts/evaluate.py
pytest
```

## 项目结构

```text
.
├── main.py
├── src/fault_diagnosis_agent/
│   ├── api.py
│   ├── diagnosis.py
│   ├── graph.py
│   ├── llm.py
│   ├── models.py
│   └── retrieval/
├── scripts/
│   ├── build_knowledge_base.py
│   ├── draw_graph.py
│   └── evaluate.py
├── data/
│   ├── processed/fault_knowledge.json
│   └── eval/test_cases.json
├── docs/
└── tests/
```

## 配置 LLM

复制 `.env.example` 并设置环境变量：

```bash
set OPENAI_API_KEY=your_key
set OPENAI_MODEL=gpt-4o-mini
```

当前代码不会强制依赖 LLM，便于离线演示和维护。

