# 油气田故障诊断智能问答 Agent

> 基于 FastAPI + LangGraph 的油气田设备故障诊断 RAG Agent · 开箱即用 · 可选接入任意 LLM 增强推理

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-1c3c3c?logo=openmediavault&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## 🔍 项目简介

本项目是一个面向油气田场景的故障诊断问答系统。输入自然语言故障描述，系统会自动：

- **实体识别**：从描述中提取设备、指标、阈值等关键信息
- **故障分类**：智能判断故障类型（压缩机、分离器、干管、集气站、气井积液等）
- **知识库检索**：基于 BM25 + 规则混合检索匹配最相关的处置流程
- **根因分析**：基于检索结果生成根因分析（可选 LLM 增强）
- **处置方案**：给出标准化的处置步骤和风险提示
- **全链路可视化**：实时追踪推理过程的每一步决策

> 💡 **核心优势**：无需配置 API Key 也能完整运行（本地规则模式）；配置 API Key 后自动切换到 LLM 增强模式，兼容所有 OpenAI 兼容接口。

---

## ✨ 功能特性

### 核心功能

- 📝 **自然语言故障问答**：输入描述即返回完整诊断报告
- 📊 **全链路追踪可视化**：查看实体提取、故障分类、检索打分、推理过程的每一步
- 📚 **知识库浏览与管理**：结构化展示所有故障处置流程
- 🔧 **Word 知识库导入**：将运维手册中的故障处理流程解析为结构化 JSON

### 技术亮点

- 🔌 **LLM 即插即用**：支持 OpenAI、DeepSeek、智谱、通义千问、月之暗面、百度千帆、Ollama 等所有 OpenAI 兼容接口，仅需环境变量配置
- 🌐 **零依赖部署**：本地规则模式下无需任何外部 API，可完全离线运行
- ⚡ **LangGraph 状态机**：分类 → 信息补全 → 检索 → 推理 → 方案生成 → 回答 的完整工作流
- 🎨 **纯前端可视化**：无需 npm，原生 HTML + CSS + JS，开箱即用

---

## 🏗️ 系统架构

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────┐
│  LangGraph 状态机                                │
│                                                   │
│  [实体提取] → [故障分类] → [是否需追问?]         │
│                          │                           │
│                          ├─ YES → 返回追问信息        │
│                          └─ NO  → [知识库检索]        │
│                                       │                │
│                                       ▼                │
│                                  [根因推理] ←─── LLM (可选)
│                                       │                │
│                                       ▼                │
│                                  [方案生成]             │
│                                       │                │
│                                       ▼                │
│                                  [最终回答]             │
└─────────────────────────────────────────────────┘
    │
    ▼
FastAPI API / 前端可视化页面
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 任意现代浏览器（Chrome / Edge / Firefox）

### 步骤 1：克隆并安装依赖

```bash
# 克隆或下载项目
cd fault-diagnosis-agent

# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS / Linux

# 安装核心依赖
pip install -e .

# 如需 LLM 增强，额外安装：
# pip install langchain-openai>=0.1.20
```

### 步骤 2：启动服务

```bash
uvicorn main:app --reload
```

启动成功后你会看到：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 步骤 3：打开前端

在浏览器中访问：

- **首页**：http://127.0.0.1:8000/
- **API 文档**：http://127.0.0.1:8000/docs

### 步骤 4：测试诊断

在首页点击 **「RAG 诊断追踪」**，输入故障描述：

```
压缩机压力过高报警怎么办？
```

点击执行，即可看到完整推理过程。

---

## 🧠 配置 LLM（可选）

本项目不强制绑定任何 LLM 服务商。你可以自由选择：

### 方式 1：不配置 — 本地规则模式（默认）

**什么都不用做！** 系统自动使用本地知识库 + 规则推理，可完全离线运行。

诊断质量依赖知识库内容，根因分析直接提取文档中的结论。

### 方式 2：配置 API Key — LLM 增强模式

复制 `.env.example` 为 `.env`，然后填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，任选一家服务商：

| 服务商 | `LLM_BASE_URL` | `LLM_MODEL` 示例 |
|--------|----------------|-----------------|
| **OpenAI** | （留空） | `gpt-4o-mini` |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` |
| **智谱 AI** | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| **月之暗面 Kimi** | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| **通义千问** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| **百度千帆** | `https://qianfan.baidubce.com/v2` | （千帆模型 ID） |
| **Ollama (本地)** | `http://localhost:11434/v1` | `qwen2.5`, `llama3` |
| **LM Studio** | `http://localhost:1234/v1` | （本地加载的模型） |
| **vLLM / 自部署** | （你的服务地址） | （你的模型名） |

`.env` 文件完整示例：
```env
# API 密钥（Ollama 等本地服务填任意非空字符串即可）
LLM_API_KEY=sk-your-api-key-here

# 自定义 API 端点（OpenAI 官方留空即可）
LLM_BASE_URL=https://api.deepseek.com/v1

# 模型名称
LLM_MODEL=deepseek-chat
```

配置完成后，**重启 uvicorn** 即可自动启用 LLM 增强。

> 🔐 **安全提醒**：`.env` 文件包含密钥，已在 `.gitignore` 中排除，请勿提交到 GitHub！

---

## 📚 导入自定义知识库

项目内置了一份示例知识库（`data/processed/fault_knowledge.json`）。如需导入你自己的 Word 文档：

1. 将 `.docx` 文件放入 `data/raw/` 目录
2. 执行导入脚本：

```bash
python scripts/build_knowledge_base.py --doc data/raw/你的文档.docx --output data/processed/fault_knowledge.json
```

3. 重启服务即可生效

文档格式要求：
- 以标题层级组织故障类型（如「1. 压缩机压力高报警」）
- 每条流程包含「故障现象」「根因分析」「处置步骤」「风险提示」
- 支持标准的 Word 标题样式（Heading 1~3）

---

## 📖 API 文档

### 主要接口

| 方法 | 路径 | 说明 |
|:----:|:-----|:-----|
| `GET` | `/` | 首页（前端可视化） |
| `GET` | `/health` | 健康检查 |
| `POST` | `/diagnose` | 故障诊断（返回最终答案） |
| `POST` | `/diagnose/trace` | 故障诊断 + 全链路追踪 |
| `POST` | `/feedback` | 提交反馈评分 |
| `GET` | `/kb/stats` | 知识库统计信息 |
| `GET` | `/kb/items` | 知识库条目列表 |
| `GET` | `/kb/items/{id}` | 单个知识库条目详情 |

### 请求示例

```bash
curl -X POST http://127.0.0.1:8000/diagnose/trace \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分离器液位高报警",
    "session_id": "test001",
    "top_k": 5
  }'
```

### 响应结构

```json
{
  "answer": {
    "fault_type": "separator_level_high",
    "root_cause": "...",
    "steps": ["步骤1", "步骤2", "..."],
    "risk": "..."
  },
  "trace": {
    "entities": { "device": "分离器", "indicator": "液位" },
    "classification": { "matched_keywords": [...], "score": 0.85 },
    "retrieval": { "documents": [...], "top_results": [...] },
    "reasoning": { "assembled_root_cause": "..." },
    "solution": { "steps_from_kb": [...] },
    "duration_ms": 123.45
  }
}
```

---

## 📁 项目结构

```
fault-diagnosis-agent/
├── main.py                          # FastAPI 应用入口
├── requirements.txt                 # 依赖清单
├── pyproject.toml                   # Python 项目配置
├── .env.example                     # 环境变量模板（复制为 .env 使用）
├── .gitignore                       # Git 忽略规则
│
├── src/fault_diagnosis_agent/       # 核心源码包
│   ├── api.py                       # API 路由定义
│   ├── config.py                    # 配置管理（LLM、知识库路径）
│   ├── llm.py                       # 可选 LLM 客户端（多提供商兼容）
│   ├── models.py                    # Pydantic 数据模型
│   ├── diagnosis.py                 # RAG 推理管线与节点逻辑
│   ├── graph.py                     # LangGraph 工作流定义
│   ├── prompts.py                   # LLM 提示词模板
│   └── retrieval/                   # 检索子模块
│       ├── entity_extractor.py      # 实体提取
│       ├── fault_types.py           # 故障类型分类
│       ├── hybrid_retriever.py      # BM25 + 规则混合检索器
│       └── document_processor.py    # 文档处理工具
│
├── static/                          # 前端静态文件（纯 HTML/JS/CSS）
│   ├── index.html                   # 首页
│   ├── trace.html                   # RAG 追踪页面
│   ├── kb.html                      # 知识库总览
│   ├── items.html                   # 知识库条目浏览
│   ├── debug.html                   # 查询调试器
│   ├── css/style.css                # 样式表
│   └── js/                          # JavaScript 脚本
│
├── scripts/                         # 工具脚本
│   ├── build_knowledge_base.py      # Word → JSON 知识库构建
│   ├── draw_graph.py                # 绘制 LangGraph 流程图
│   └── evaluate.py                  # 评估脚本
│
├── data/                            # 数据目录
│   ├── processed/fault_knowledge.json  # 结构化知识库
│   ├── eval/test_cases.json         # 测试用例
│   ├── raw/                         # 原始 Word 文档
│   └── feedback/                    # 用户反馈数据
│
├── tests/                           # 单元测试
│   ├── test_diagnosis.py
│   └── test_entity_extractor.py
│
└── docs/                            # 附加文档
    ├── fault_diagnosis_graph.md
    └── trae_development_log.md
```

---

## 🧪 测试与评估

运行内置测试：

```bash
# 运行所有单元测试
pytest

# 运行评估脚本（20+ 测试场景）
python scripts/evaluate.py
```

---

## 🛠️ 开发指南

### 添加新的故障类型

1. 在 `data/processed/fault_knowledge.json` 中添加新条目
2. 或编辑 `scripts/build_knowledge_base.py` 支持更多文档格式

### 扩展 LLM 提供商

所有 OpenAI 兼容的接口都能直接使用。如果你的服务商接口格式不同：

1. 在 `src/fault_diagnosis_agent/llm.py` 中扩展 `OptionalLLM` 类
2. 添加新的环境变量和初始化逻辑

### 前端二次开发

前端是纯静态页面，无构建流程，直接编辑 `static/` 目录下的 HTML/JS/CSS 文件即可。

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的改动 (`git commit -m 'feat: 增加某个很棒的特性'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启一个 Pull Request

---

## 📝 FAQ

<details>
<summary><strong>Q: 不配置 API Key 也能用吗？</strong></summary>

完全可以。系统默认使用本地规则 + 知识库检索，能给出完整的诊断结论和处置步骤，只是根因分析的自然语言流畅度会比 LLM 模式稍差。
</details>

<details>
<summary><strong>Q: 支持哪些 LLM 服务商？</strong></summary>

所有提供 OpenAI 兼容接口的服务商都支持，包括：OpenAI、DeepSeek、智谱 AI、月之暗面 Kimi、通义千问、百度千帆、Ollama、LM Studio、vLLM 等。
</details>

<details>
<summary><strong>Q: 如何切换 LLM 服务商？</strong></summary>

只需修改 `.env` 文件中的 `LLM_BASE_URL`、`LLM_MODEL`、`LLM_API_KEY`，然后重启 `uvicorn` 即可，不需要修改任何代码。
</details>

<details>
<summary><strong>Q: 知识库可以自定义吗？</strong></summary>

可以。参考「导入自定义知识库」章节，将 Word 文档导入即可。也可以直接编辑 `data/processed/fault_knowledge.json` 的 JSON 内容。
</details>

<details>
<summary><strong>Q: 能在纯离线环境部署吗？</strong></summary>

能。不配置 API Key 时，系统零外部依赖，完全离线运行。
</details>

---

## 📄 License

MIT License © 油气田故障诊断项目

---

<div align="center">
  <strong>如果本项目对你有帮助，欢迎 ⭐ Star</strong>
</div>
