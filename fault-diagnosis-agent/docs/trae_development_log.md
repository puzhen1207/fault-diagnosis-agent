# Trae 开发记录

本项目按需求文档中的 Trae Builder / Chat 思路整理为可维护工程，但当前代码由 Codex 直接实现。

## Builder 阶段目标

- 生成油气田故障诊断 RAG Agent 项目骨架。
- 包含 Word 文档解析、故障分类、LangGraph 状态机和 FastAPI 接口。

## Chat 迭代目标

- 将《知识.docx》解析为结构化 JSON 知识库。
- 根据真实运维文档补充故障类型、根因、处置步骤和风险提示。
- 对 Prompt 进行 A/B 测试，重点约束禁止臆造设备参数和禁止省略观察步骤。

## 当前实现说明

- 已内置一份可演示的结构化知识库。
- `scripts/build_knowledge_base.py` 可将真实 Word 文档转换为 `data/processed/fault_knowledge.json`。
- 未配置 LLM 时使用确定性规则运行；配置 OpenAI Key 后可增强根因分析表达。

