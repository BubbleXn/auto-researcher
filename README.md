# AutoResearcher

AI 驱动的自动化研究报告生成系统。输入一个研究主题，系统会自动规划研究方案、检索信息、批判性验证、收集人工反馈，最终生成一份结构化的研究报告。

---

## 核心特性

- **智能工作流**：Planner → Searcher → Critic → HumanFeedback → Writer
- **实时反馈**：基于 Server-Sent Events (SSE) 的流式状态更新
- **持久化状态**：使用 SQLite 保存 LangGraph 检查点，支持断线重连
- **文档上传**：支持 PDF 解析与向量化存储
- **生产级加固**：请求日志、超时重试、健康检查、文件上传安全校验

---

## 技术栈

### 后端

- Python 3.12
- FastAPI
- LangGraph
- Pydantic
- ChromaDB
- PyMuPDF
- Tavily Search API
- OpenAI 兼容接口（支持阿里云 AI Studio 等）

### 前端

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS

---

## 项目结构

```
.
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── agent/          # LangGraph 工作流与节点
│   │   ├── api/            # REST API 路由
│   │   ├── core/           # 配置与依赖注入
│   │   ├── models/         # Pydantic 模型
│   │   └── services/       # 业务服务（PDF 解析等）
│   ├── tests/              # 单元测试与集成测试
│   ├── .env.example        # 环境变量模板
│   └── pyproject.toml
├── frontend/                # Next.js 前端
│   ├── src/
│   │   ├── app/            # 页面路由
│   │   ├── components/     # React 组件
│   │   ├── hooks/          # 自定义 Hooks
│   │   ├── lib/            # 工具函数
│   │   ├── mocks/          # 本地 Mock 数据
│   │   └── types/          # TypeScript 类型定义
│   └── package.json
└── docs/
    └── sse-event-protocol.md  # SSE 事件协议文档
```

---

## 快速开始

### 1. 启动 ChromaDB（Docker）

```bash
docker run -d --name chromadb \
  -p 8001:8000 \
  -v chromadb_data:/chroma/chroma \
  --restart unless-stopped \
  chromadb/chroma:latest
```

### 2. 配置后端

```bash
cd backend
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```bash
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://aistudio.alibaba-inc.com/api/openai/v1  # 可选
OPENAI_MODEL=qwen3-coder-plus                                   # 可选
TAVILY_API_KEY=tvly-your-key

CHROMADB_HOST=localhost
CHROMADB_PORT=8001
```

> 如果没有真实 API Key，可以在 `.env` 中设置 `USE_MOCK=true` 启用 Mock 模式。

### 3. 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问 `http://localhost:3000`。

---

## 测试

### 后端测试

```bash
cd backend
pytest -q
```

### 前端类型检查

```bash
cd frontend
npm run typecheck
```

---

## 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 是* | LLM API Key |
| `OPENAI_BASE_URL` | 否 | OpenAI 兼容接口地址 |
| `OPENAI_MODEL` | 否 | 模型名称，默认 `gpt-4o` |
| `TAVILY_API_KEY` | 是* | Tavily 搜索 API Key |
| `CHROMADB_HOST` | 否 | ChromaDB 地址，默认 `chromadb` |
| `CHROMADB_PORT` | 否 | ChromaDB 端口，默认 `8001` |
| `USE_MOCK` | 否 | 设为 `true` 启用 Mock 模式 |
| `MAX_UPLOAD_SIZE_MB` | 否 | 上传文件大小限制，默认 `50` |

\* Mock 模式下可不填。

---

## 协作开发规范

本项目采用 Pull Request 工作流：

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交代码并推送
4. 发起 Pull Request 到 `main` 分支
5. 等待代码评审通过

---

## 许可证

MIT
