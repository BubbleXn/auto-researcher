# SSE Event Protocol — AutoResearcher

**Version**: 1.0 (D3 Draft)
**Author**: Backend Engineer
**Date**: 2026-07-21
**Status**: D3 Initial Draft — pending review from Frontend (D4) and QA (D4-D5)

---

## 1. Transport

- **Endpoint**: `POST /api/research/start`
- **Content-Type (request)**: `application/json`
- **Content-Type (response)**: `text/event-stream`
- **Request Body**:
  ```json
  {
    "query": "string (required, 1-2000 chars)",
    "resume_from_event_id": "integer (optional, for reconnection)"
  }
  ```
- **Response Headers**:
  ```
  Content-Type: text/event-stream
  Cache-Control: no-cache
  Connection: keep-alive
  X-Accel-Buffering: no
  ```

### 1.1 Wire Format

Standard SSE format. Each event:

```
event: <event_type>
data: <JSON payload>

```

All payloads are JSON objects. Every payload contains base fields:

| Field | Type | Description |
|:---|:---|:---|
| `event_id` | `integer` | Monotonically increasing per research session, starting from 1 |
| `timestamp` | `string` | ISO 8601 UTC, e.g. `"2026-07-21T10:30:00.123Z"` |

---

## 2. Event Types (9 total)

### 2.1 `research_start`

First event of a new session. MUST be the first event pushed.

```json
{
  "event_id": 1,
  "timestamp": "2026-07-21T10:30:00.000Z",
  "research_id": "uuid-string",
  "query": "分析2024年电动汽车电池技术路线对比"
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `research_id` | `string (UUID)` | yes | Unique identifier for this research session |
| `query` | `string` | yes | Original user query |

---

### 2.2 `phase_change`

Signals transition between workflow phases.

```json
{
  "event_id": 2,
  "timestamp": "2026-07-21T10:30:00.100Z",
  "phase": "planning",
  "from_phase": null,
  "message": "正在分析问题并制定研究计划..."
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `phase` | `string` | yes | New phase. One of: `planning`, `searching`, `critiquing`, `writing`, `awaiting_human_input`, `completed`, `error` |
| `from_phase` | `string \| null` | yes | Previous phase. `null` on first transition |
| `message` | `string` | yes | Human-readable description (Chinese) |

---

### 2.3 `agent_step`

Granular operation within a phase. Multiple steps per phase.

```json
{
  "event_id": 5,
  "timestamp": "2026-07-21T10:30:01.500Z",
  "step_id": "planner_1721558401500",
  "node": "planner",
  "action": "plan_created",
  "detail": "已生成 3 个子研究任务",
  "intermediate_result": {
    "outline": ["锂电池技术现状", "固态电池发展进展", "主要厂商技术路线对比"]
  }
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `step_id` | `string` | yes | Unique. Format: `{node_name}_{timestamp_ms}` |
| `node` | `string` | yes | LangGraph node name |
| `action` | `string` | yes | Machine-readable action name. Frontend maps to icons |
| `detail` | `string` | yes | Human-readable description (Chinese) |
| `intermediate_result` | `object \| null` | no | Optional structured data for debugging / display |

**Known `action` values**: `plan_created`, `search_started`, `search_completed`, `pdf_parsed`, `conflict_detected`, `retry_triggered`, `writing_report`

---

### 2.4 `progress`

Sub-task progress within a phase (primarily `searching`).

```json
{
  "event_id": 7,
  "timestamp": "2026-07-21T10:30:03.200Z",
  "current": 2,
  "total": 5,
  "detail": "搜索: 固态电池技术发展进展"
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `current` | `integer` | yes | Current sub-task index (1-based) |
| `total` | `integer` | yes | Total sub-tasks |
| `detail` | `string` | yes | Description of current sub-task (Chinese) |

---

### 2.5 `human_input_needed`

Pauses the workflow, waits for user feedback.

```json
{
  "event_id": 12,
  "timestamp": "2026-07-21T10:30:10.000Z",
  "input_id": "uuid-research_id-input-1",
  "prompt": "请确认以下研究大纲，可以直接修改后提交：",
  "outline": [
    {"section": "锂电池技术现状", "key_points": ["能量密度", "成本趋势"]},
    {"section": "固态电池发展进展", "key_points": ["量产时间线", "技术瓶颈"]}
  ],
  "editable_fields": ["outline"]
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `input_id` | `string` | yes | Unique ID. Frontend sends back in feedback POST |
| `prompt` | `string` | yes | Question / instruction for the user |
| `outline` | `array` | yes | Current research outline for editing |
| `editable_fields` | `array[string]` | yes | Which fields the user can modify |

**Backend behavior**: Coroutine suspends. No further events pushed until feedback received via `POST /api/research/feedback`. No timeout — waits indefinitely (MVP).

**Feedback endpoint**:
```
POST /api/research/feedback
{
  "research_id": "...",
  "input_id": "...",
  "feedback": "string (user text)",
  "modified_outline": [...] (optional)
}
```

---

### 2.6 `report_chunk`

Streaming report content (Markdown).

```json
{
  "event_id": 18,
  "timestamp": "2026-07-21T10:31:00.500Z",
  "chunk": "## 1. 锂电池技术现状\n\n目前主流的锂电池技术...",
  "chunk_index": 0,
  "is_final": false
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `chunk` | `string` | yes | Markdown fragment |
| `chunk_index` | `integer` | yes | 0-based sequence number. For dedup on reconnection |
| `is_final` | `boolean` | yes | `true` on the last chunk. **Use this to detect completion, not `chunk_index`** |

---

### 2.7 `error`

Error event. Separate from the normal event flow.

```json
{
  "event_id": 10,
  "timestamp": "2026-07-21T10:30:05.000Z",
  "error_code": "SEARCH_FAILED",
  "message": "Tavily API 请求超时，搜索任务 3/5 失败",
  "recoverable": true,
  "detail": "ConnectionTimeout: api.tavily.com"
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `error_code` | `string` | yes | UPPER_SNAKE_CASE. See error code table below |
| `message` | `string` | yes | User-visible description (Chinese) |
| `recoverable` | `boolean` | yes | `true` = frontend shows retry. `false` = terminal |
| `detail` | `string \| null` | no | Technical detail for debugging |

**Error codes**:

| Code | Recoverable | Description |
|:---|:---|:---|
| `SEARCH_FAILED` | true | Web search API failure |
| `LLM_RATE_LIMITED` | true | LLM API rate limit hit |
| `LLM_GENERATION_FAILED` | true | LLM returned invalid / empty response |
| `PDF_PARSE_FAILED` | true | PDF document could not be parsed |
| `RESEARCH_FAILED` | false | Unrecoverable internal error |
| `MAX_RETRIES_EXCEEDED` | false | Critic node exhausted all retry attempts |
| `CHECKPOINT_CORRUPTED` | false | Cannot restore from checkpoint |

---

### 2.8 `done`

Final event. MUST be the last event pushed.

```json
{
  "event_id": 22,
  "timestamp": "2026-07-21T10:31:30.000Z",
  "research_id": "uuid-string",
  "total_sources": 12,
  "total_duration_seconds": 90.5
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `research_id` | `string` | yes | Session ID |
| `total_sources` | `integer` | yes | Number of unique sources cited |
| `total_duration_seconds` | `float` | yes | Wall-clock time |

---

### 2.9 `resume_state` (Reconnection only)

Pushed as the FIRST event after a reconnection. Provides state context so the frontend can rebuild its UI without replaying history.

```json
{
  "event_id": 15,
  "timestamp": "2026-07-21T10:30:45.000Z",
  "research_id": "uuid-string",
  "resumed": true,
  "phase": "critiquing",
  "retry_count": 2,
  "max_retries": 3,
  "completed_steps": [
    {"step_id": "planner_1721558401500", "action": "plan_created", "detail": "已生成 3 个子研究任务"},
    {"step_id": "searcher_1721558402000", "action": "search_completed", "detail": "5 个子任务搜索完成"},
    {"step_id": "critic_1721558405000", "action": "conflict_detected", "detail": "发现 2 处信息冲突"}
  ],
  "pending_sub_tasks": [
    {"id": "task_3", "query": "主要厂商技术路线对比", "status": "pending"}
  ],
  "report_so_far": ""
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `resumed` | `boolean` | yes | Always `true` |
| `phase` | `string` | yes | Current phase at time of reconnection |
| `retry_count` | `integer` | yes | Current Critic retry count |
| `max_retries` | `integer` | yes | Maximum allowed retries |
| `completed_steps` | `array` | yes | Summary of already-completed steps (step_id + action + detail) |
| `pending_sub_tasks` | `array` | yes | Sub-tasks not yet completed |
| `report_so_far` | `string` | yes | Accumulated report markdown (empty if not yet in writing phase) |

---

## 3. Event State Machine

```
                    ┌─────────────────────────────────────────────────┐
                    │           [Any State] ──disconnect──► DISCONNECTED │
                    │           DISCONNECTED ──reconnect──► resume_state │
                    │           resume_state ──► {original phase}       │
                    └─────────────────────────────────────────────────┘

    research_start ──► phase_change(planning)
                            │
                            ▼
                     agent_step(planner) ───► phase_change(searching)
                                                     │
                                    ┌────────────────┤
                                    ▼                ▼
                              progress(1..N)   agent_step(searcher)
                                    │                │
                                    └───────┬────────┘
                                            ▼
                                 ┌──► phase_change(critiquing)
                                 │          │
                                 │          ▼
                                 │    agent_step(critic)
                                 │          │
                                 │    ┌─────┴─────┐
                                 │    ▼           ▼
                                 │  [pass]    [conflict / retry]
                                 │    │           │
                                 │    │     retry_count < max?
                                 │    │      yes ─┤─── no ──► error(MAX_RETRIES_EXCEEDED) ──► done
                                 │    │           │
                                 │    │    phase_change(searching) ──► (re-search loop)
                                 │    │           │
                                 │    │           └──────────────────────────────────────┘
                                 │    ▼
                                 │  phase_change(awaiting_human_input)
                                 │          │
                                 │          ▼
                                 │  human_input_needed
                                 │          │
                                 │    [wait for feedback POST]
                                 │          │
                                 │          ▼
                                 │  phase_change(writing)
                                 │          │
                                 │          ▼
                                 │  agent_step(writer) + report_chunk(0..N, is_final=false)
                                 │          │
                                 │          ▼
                                 │  report_chunk(is_final=true)
                                 │          │
                                 │          ▼
                                 │  phase_change(completed)
                                 │          │
                                 │          ▼
                                 └───────  done

    At any point:  error(recoverable=true)  ──► system retries internally, flow continues
                   error(recoverable=false) ──► done
```

### 3.1 Legal Phase Transitions

| From | To | Trigger |
|:---|:---|:---|
| `(start)` | `planning` | Session begins |
| `planning` | `searching` | Plan complete |
| `searching` | `critiquing` | All sub-tasks searched |
| `critiquing` | `searching` | Conflict detected, retry (retry_count < max) |
| `critiquing` | `awaiting_human_input` | Critique passed |
| `awaiting_human_input` | `writing` | User feedback received |
| `writing` | `completed` | Report finalized |
| Any | `error` | Unrecoverable failure |

### 3.2 Illegal Transitions (contract test assertions)

- `planning` → `writing` (must pass through `searching` + `critiquing`)
- `searching` → `writing` (must pass through `critiquing`)
- `human_input_needed` followed by ANY event other than feedback response or disconnect
- `done` followed by any event
- `research_start` appearing anywhere other than position 1

---

## 4. Reconnection Protocol

### 4.1 Client Behavior

1. Client tracks `event_id` of last received event
2. On disconnect: exponential backoff retry (1s → 2s → 4s → 8s → 16s, max 5 attempts)
3. Reconnect request: `POST /api/research/start` with `resume_from_event_id` in body
4. On receiving `resume_state`: rebuild completed steps UI, resume from current phase
5. User-initiated `disconnect()` does NOT trigger reconnection

### 4.2 Backend Behavior

1. Receive `resume_from_event_id` in request body
2. Load state from SQLite checkpoint
3. Push `resume_state` as first event (event_id = resume_from_event_id + 1)
4. Continue from current phase, only push new events (NO history replay)
5. If checkpoint not found or corrupted: push `error(CHECKPOINT_CORRUPTED)` → `done`

### 4.3 Edge Case: Reconnect During Critic Retry

If client disconnects while Critic is in retry loop (e.g., retry 2 of 3):
- `resume_state` reports `phase: "critiquing"`, `retry_count: 2`
- `completed_steps` includes steps from ALL prior retries
- Frontend renders completed retry steps in "done" state, then receives incremental events for the current retry

---

## 5. Appendix: Frontend Action → Icon Mapping Reference

| `action` value | Suggested icon | Phase |
|:---|:---|:---|
| `plan_created` | 📋 list/outline | planning |
| `search_started` | 🔍 magnifier | searching |
| `search_completed` | ✅ checkmark | searching |
| `pdf_parsed` | 📄 document | searching |
| `conflict_detected` | ⚠️ warning | critiquing |
| `retry_triggered` | 🔄 refresh | critiquing |
| `writing_report` | ✍️ pen | writing |
