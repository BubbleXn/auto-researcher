# Phase 1 实施计划：AutoResearcher 核心功能补全

## Context

项目处于 W1+W2 baseline 状态，基础链路 Planner→Searcher→Writer 已跑通。阶段一目标是补全三个 P0 核心功能（Critic 自纠错、PDF 解析、人机协作）和三个 P1 体验优化（ChromaDB 集成、报告预览、思考链 UI），使用户能完成一次完整的深度研究流程。

所有开发和测试走 mock，不消耗 API 额度。

## 依赖关系与执行顺序

```
Step 1: Task 1 (Critic) + Task 3 (PDF 解析)  — 并行开发
Step 2: Task 2 (人机协作)                    — 依赖 Task 1
Step 3: Task 4 (ChromaDB) + Task 5 (报告) + Task 6 (UI 打磨)  — 并行开发
```

---

## Task 1: Critic 节点 (P0 - 后端)

### 新建文件

**`backend/app/agent/nodes/critic.py`**
- 类 `CriticNode(llm: LLMClient)`，遵循现有节点模式（构造注入 + `__call__` 返回 state dict）
- Prompt 要求 LLM 以 JSON 返回 `CritiqueResult` 结构（`has_conflicts`, `conflicts`, `missing_aspects`, `confidence_score`, `recommendation`）
- 调用 `self._llm.generate_structured()` 评估搜索结果
- SSE 事件：`PHASE_CHANGE`(→critiquing) + `AGENT_STEP`(action=`conflict_detected` 或 `retry_triggered`)
- 分支逻辑：
  - `recommendation == "proceed"` → phase = writing（Task 2 完成后改为 awaiting_human_input）
  - `recommendation == "retry_search"` 且 `retry_count < max_retries` → phase = searching，retry_count+1，重置相关 sub_tasks 为 pending
  - `retry_count >= max_retries` → 发 ERROR(MAX_RETRIES_EXCEEDED)，phase = error

**`backend/tests/unit/test_critic.py`**
- 复用 `test_planner.py` 中 `MockLLMClient` 模式
- 测试：高置信通过、触发重试、最大重试错误、SSE 事件合规性、event_id 单调递增

### 修改文件

**`backend/app/agent/graph.py`**
- 导入 CriticNode，实例化 `critic = CriticNode(llm=llm)`
- 加节点 `graph.add_node("critic", critic)`
- 删除 `graph.add_edge("searcher", "writer")`
- 加 `graph.add_edge("searcher", "critic")`
- 加条件边 `graph.add_conditional_edges("critic", _route_after_critic)` — 路由函数检查 `critique.recommendation` + `retry_count` 决定去 searcher/writer/END

**`backend/app/agent/nodes/searcher.py`**
- `from_phase` 根据 `retry_count > 0` 判断：首次来自 planning，重试来自 critiquing
- 如 state 中有 `critique.missing_aspects`，追加为额外搜索子任务

---

## Task 2: 人机协作交互 (P0 - 前端+后端)

### 架构决策

使用 **asyncio.Event** 实现暂停/恢复，而非 LangGraph `interrupt()`。原因：interrupt 需要 checkpointer，MemorySaver 进程重启丢状态，SqliteSaver 属于阶段二范围。asyncio.Event 方案简单、与当前流式架构兼容、Phase 2 可平滑迁移。

### 新建文件

**`backend/app/core/session_registry.py`**
- 共享会话注册表：`_active_sessions: dict[str, dict]`，提供 `get_session()`/`remove_session()`
- 解决 research.py 与 human_feedback.py 之间的循环引用问题

**`backend/app/agent/nodes/human_feedback.py`**
- 类 `HumanFeedbackNode`（无需 client 注入）
- 发 `PHASE_CHANGE`(→awaiting_human_input) + `HUMAN_INPUT_NEEDED` 事件（携带 outline）
- 通过 event_queue 立即推送事件到 SSE 流
- 创建 `asyncio.Event` 注册到 session_registry，`await event.wait()` 阻塞
- 收到反馈后读取 feedback/modified_outline，更新 plan，返回 phase=writing

**`backend/tests/unit/test_human_feedback.py`**

### 修改文件

**`backend/app/agent/graph.py`**
- 加节点 human_feedback，Critic pass 时路由到 human_feedback 而非 writer
- 加边 `human_feedback → writer`

**`backend/app/api/research.py`**
- 迁移 `_active_research` 到 session_registry
- `submit_feedback()` 端点：存储 feedback 后 `event.set()` 唤醒等待的协程

**`backend/app/agent/state.py`**
- ResearchPhase 枚举加 `AWAITING_HUMAN_INPUT = "awaiting_human_input"`

**`backend/app/models/schemas.py`**
- HumanFeedbackRequest 加 `input_id: str | None = None`

**`frontend/src/types/sse-events.ts`**
- ResearchPhase 加 `"awaiting_human_input"`

**`frontend/src/lib/constants.ts`**
- PHASE_LABELS/PHASE_COLORS/PHASE_BG_COLORS 补充 `awaiting_human_input` 条目

**`frontend/src/app/page.tsx`**
- submitInput/skipInput 增加 `fetch(HUMAN_INPUT_ENDPOINT, ...)` 实际调用后端

**`frontend/src/mocks/mock-data.ts`**
- 调整事件序列：加入 critiquing 阶段事件，human_input_needed 移到 critiquing 之后

**`frontend/src/mocks/mock-sse-server.ts`**
- 添加 `POST /api/research/feedback` mock 处理

---

## Task 3: PDF 本地解析 (P0 - 后端)

### 新建文件

**`backend/app/services/pdf_parser.py`**
- 类 `PDFParser(chunk_size=1000, chunk_overlap=200)`
- `parse(pdf_bytes, filename) -> list[TextChunk]`：PyMuPDF 提取文本 → 按页分段 → 重叠切块
- `TextChunk` dataclass：id, text, metadata(page_number, source_filename, chunk_index)

**`backend/app/api/documents.py`**
- 路由 `APIRouter(prefix="/api/documents")`
- `POST /upload`：接收 `UploadFile`，校验 PDF，解析后存入 VectorStore

**`backend/tests/unit/test_pdf_parser.py`** — 内存生成 PDF 测试
**`backend/tests/unit/test_documents_api.py`** — httpx.AsyncClient + mock VectorStore

### 修改文件

**`backend/app/models/schemas.py`** — 新增 `DocumentUploadResponse`
**`backend/app/main.py`** — 注册 documents_router

---

## Task 4: ChromaDB 集成 (P1 - 后端)

### 修改文件

**`backend/app/agent/nodes/searcher.py`** — 构造加 `vectorstore`，搜索后存储结果
**`backend/app/agent/nodes/writer.py`** — 构造加 `vectorstore`，生成前查询 PDF/历史内容追加上下文
**`backend/app/agent/graph.py`** — 传 vectorstore 到 SearcherNode/WriterNode
**`backend/tests/unit/test_searcher.py`** — 扩展 vectorstore 测试
**新建 `backend/tests/unit/test_writer.py`** — Writer 完整单测 + MockVectorStoreClient

---

## Task 5: 报告预览优化 (P1 - 前端)

**`frontend/src/components/report/ReportView.tsx`** — 自定义 `a` 渲染器（引用高亮 + 来源提示）
**`frontend/src/types/research.ts`** — ResearchSession 加 `sources`
**`frontend/src/app/globals.css`** — 引用高亮样式

---

## Task 6: 思考链 UI 打磨 (P1 - 前端)

**`frontend/src/components/chat/AgentStep.tsx`** — 淡入动画 + action→icon 映射
**`frontend/src/components/chat/PhaseBlock.tsx`** — awaiting_human_input 暂停图标 + 错误状态
**`frontend/src/components/chat/ProgressBar.tsx`** — 百分比标签 + 阶段颜色
**`frontend/src/app/globals.css`** — fade-in keyframe

---

## 文件统计

- 新建：12 个文件（5 源码 + 7 测试）
- 修改：~17 个文件

## 验证方案

1. **后端单测**：`cd backend && python -m pytest tests/ -v` — 全 mock
2. **集成测试**：mock LLM 先返回 retry → proceed，验证重试循环+人机交互全流程
3. **前端验证**：`npm run mock-sse` + 浏览器验证完整流程
4. **类型检查**：`npm run typecheck` 确保类型一致
