import type { SSEEvent } from "@/types/sse-events";

export const MOCK_QUERY = "大语言模型在代码生成领域的最新进展与技术对比";

const ts = (offset: number) =>
  new Date(Date.now() + offset * 1000).toISOString();

export function createMockEventSequence(): Array<{
  event: SSEEvent;
  delay: number;
}> {
  return [
    {
      delay: 200,
      event: {
        type: "research_start",
        research_id: "mock-001",
        query: MOCK_QUERY,
        timestamp: ts(0),
      },
    },
    {
      delay: 500,
      event: {
        type: "phase_change",
        phase: "planning",
        from_phase: null,
        timestamp: ts(0.5),
      },
    },
    {
      delay: 800,
      event: {
        type: "agent_step",
        phase: "planning",
        step_id: "p1",
        action: "decompose",
        detail: "分析研究主题，拆解为 4 个子问题...",
        timestamp: ts(1.3),
      },
    },
    {
      delay: 600,
      event: {
        type: "agent_step",
        phase: "planning",
        step_id: "p2",
        action: "outline",
        detail:
          "生成大纲：1.背景与现状 2.主流模型对比 3.评测基准 4.未来趋势",
        timestamp: ts(1.9),
      },
    },
    {
      delay: 400,
      event: {
        type: "phase_change",
        phase: "searching",
        from_phase: "planning",
        timestamp: ts(2.3),
      },
    },
    {
      delay: 1000,
      event: {
        type: "agent_step",
        phase: "searching",
        step_id: "s1",
        action: "web_search",
        detail: "搜索：LLM code generation 2024 benchmark",
        timestamp: ts(3.3),
      },
    },
    {
      delay: 500,
      event: {
        type: "progress",
        phase: "searching",
        current: 1,
        total: 4,
        detail: "搜索: 代码生成模型基准测试",
      },
    },
    {
      delay: 800,
      event: {
        type: "agent_step",
        phase: "searching",
        step_id: "s2",
        action: "web_search",
        detail: "搜索：GPT-4 vs Claude vs Gemini coding comparison",
        timestamp: ts(4.6),
      },
    },
    {
      delay: 500,
      event: {
        type: "progress",
        phase: "searching",
        current: 2,
        total: 4,
        detail: "搜索: 主流模型编码能力对比",
      },
    },
    {
      delay: 800,
      event: {
        type: "agent_step",
        phase: "searching",
        step_id: "s3",
        action: "web_search",
        detail: "搜索：代码生成安全性与可靠性研究",
        timestamp: ts(5.9),
      },
    },
    {
      delay: 500,
      event: {
        type: "progress",
        phase: "searching",
        current: 3,
        total: 4,
        detail: "搜索: 代码生成安全性研究",
      },
    },
    {
      delay: 800,
      event: {
        type: "agent_step",
        phase: "searching",
        step_id: "s4",
        action: "web_search",
        detail: "搜索：AI coding assistant market trends 2024-2025",
        timestamp: ts(7.2),
      },
    },
    {
      delay: 300,
      event: {
        type: "progress",
        phase: "searching",
        current: 4,
        total: 4,
        detail: "搜索完成",
      },
    },
    {
      delay: 500,
      event: {
        type: "phase_change",
        phase: "critiquing",
        from_phase: "searching",
        timestamp: ts(8),
      },
    },
    {
      delay: 1000,
      event: {
        type: "agent_step",
        phase: "critiquing",
        step_id: "c1",
        action: "verify",
        detail: "检查信息来源权威性：发现 2 条来源可信度较低，标记处理...",
        timestamp: ts(9),
      },
    },
    {
      delay: 800,
      event: {
        type: "agent_step",
        phase: "critiquing",
        step_id: "c2",
        action: "conflict_check",
        detail: "交叉验证数据：HumanEval 评测数据存在版本差异，以最新版为准",
        timestamp: ts(9.8),
      },
    },
    {
      delay: 500,
      event: {
        type: "phase_change",
        phase: "awaiting_human_input",
        from_phase: "critiquing",
        timestamp: ts(10.3),
      },
    },
    {
      delay: 500,
      event: {
        type: "human_input_needed",
        phase: "awaiting_human_input",
        prompt:
          "已收集到 12 条相关信息。是否需要针对某个方向深入研究？可选择以下方向或自行指定：",
        input_id: "input-001",
        options: ["深入模型对比", "关注安全性", "聚焦实际应用案例", "当前信息足够"],
      },
    },
    {
      delay: 3000,
      event: {
        type: "phase_change",
        phase: "writing",
        from_phase: "awaiting_human_input",
        timestamp: ts(13.3),
      },
    },
    {
      delay: 400,
      event: {
        type: "report_chunk",
        chunk:
          "# 大语言模型在代码生成领域的最新进展\n\n## 1. 背景\n\n近年来，大语言模型（LLM）在代码生成任务中取得了显著突破。",
        chunk_index: 0,
        is_final: false,
      },
    },
    {
      delay: 300,
      event: {
        type: "report_chunk",
        chunk:
          "从早期的 Codex 到如今的 GPT-4、Claude 3.5 Sonnet 和 Gemini Pro，模型在 HumanEval、MBPP 等基准测试上的通过率已从不足 30% 提升至超过 90% [1]。\n\n",
        chunk_index: 1,
        is_final: false,
      },
    },
    {
      delay: 300,
      event: {
        type: "report_chunk",
        chunk:
          "## 2. 主流模型对比\n\n| 模型 | HumanEval | MBPP | 多语言支持 |\n|:---|:---|:---|:---|\n| GPT-4o | 90.2% | 85.7% | 优秀 |\n| Claude 3.5 Sonnet | 92.0% | 87.1% | 优秀 |\n| Gemini Pro | 84.1% | 80.3% | 良好 |\n\n",
        chunk_index: 2,
        is_final: false,
      },
    },
    {
      delay: 300,
      event: {
        type: "report_chunk",
        chunk:
          '## 3. 关键发现\n\n- **上下文理解**是当前模型间最大差异点，长上下文窗口的模型在复杂项目级代码生成中优势明显 [2]\n- **安全性**仍是主要挑战：约 15% 的生成代码存在潜在安全漏洞 [3]\n- **多语言能力**差异显著，Python 表现普遍优于其他语言\n\n## 4. 参考来源\n\n1. [HumanEval Benchmark Results 2024](https://example.com/humaneval)\n2. [Long Context Code Generation Study](https://example.com/longctx)\n3. [AI Code Security Analysis Report](https://example.com/security)\n\n---\n\n*本报告由 AutoResearcher 自动生成，请核实关键数据。*',
        chunk_index: 3,
        is_final: true,
      },
    },
    {
      delay: 500,
      event: {
        type: "done",
        research_id: "mock-001",
        report_id: "report-001",
        total_duration_seconds: 15,
        timestamp: ts(15),
      },
    },
  ];
}
