import type { SSEEvent } from "@/types/sse-events";

export const MOCK_QUERY = "大语言模型在代码生成领域的最新进展与技术对比";

const ts = (offset: number) =>
  new Date(Date.now() + offset * 1000).toISOString();

export function createPreFeedbackEvents(): Array<{
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
  ];
}

const REPORT_VARIANTS: Record<string, string[]> = {
  "深入模型对比": [
    "# 大语言模型代码生成能力深度对比\n\n## 1. 评测方法论\n\n本报告基于用户要求，重点深入对比各主流模型的代码生成能力。我们采用 HumanEval、MBPP、MultiPL-E 三大基准进行多维度评估。",
    "\n\n## 2. 详细模型对比\n\n| 模型 | HumanEval | MBPP | MultiPL-E | 长上下文 | 推理速度 |\n|:---|:---|:---|:---|:---|:---|\n| GPT-4o | 90.2% | 85.7% | 78.3% | 128K | 快 |\n| Claude 3.5 Sonnet | 92.0% | 87.1% | 82.1% | 200K | 中 |\n| Gemini Pro | 84.1% | 80.3% | 75.6% | 1M | 快 |\n| DeepSeek Coder V2 | 90.5% | 86.2% | 80.4% | 128K | 快 |\n| Llama 3.1 405B | 81.3% | 78.9% | 72.1% | 128K | 慢 |\n\n### 2.1 关键差异分析\n\n- **Claude 3.5 Sonnet** 在 HumanEval 上以 92.0% 领先，尤其擅长复杂算法和系统设计类题目 [1]",
    "\n- **GPT-4o** 在多轮对话式编程中表现最稳定，上下文保持能力优秀 [2]\n- **DeepSeek Coder V2** 作为开源模型，在代码专项任务上已接近闭源模型水平 [3]\n- **Gemini Pro** 的百万级上下文窗口在大型项目理解上具备独特优势\n\n## 3. 分语言表现\n\n| 模型 | Python | JavaScript | Rust | Java |\n|:---|:---|:---|:---|:---|\n| GPT-4o | 92% | 88% | 72% | 85% |\n| Claude 3.5 | 94% | 91% | 78% | 87% |\n| DeepSeek V2 | 91% | 85% | 75% | 83% |\n\n> Python 表现普遍最高，Rust 差距最大，体现了训练数据分布的影响。",
    "\n\n## 4. 结论\n\n综合来看，**Claude 3.5 Sonnet** 在纯代码生成精度上暂时领先，**GPT-4o** 在工程化场景中更稳定，**DeepSeek Coder V2** 是开源领域的最佳选择。选型建议根据具体场景（精度优先 vs 成本优先 vs 部署灵活性）做权衡。\n\n## 参考来源\n\n1. [HumanEval Benchmark Results 2024](https://example.com/humaneval)\n2. [GPT-4o Coding Evaluation](https://example.com/gpt4o-code)\n3. [DeepSeek Coder V2 Technical Report](https://example.com/deepseek)\n\n---\n\n*本报告根据用户选择「深入模型对比」方向生成，由 AutoResearcher 自动撰写。*",
  ],
  "关注安全性": [
    "# AI 代码生成的安全性分析报告\n\n## 1. 安全威胁全景\n\n本报告基于用户要求，重点聚焦 AI 代码生成中的安全风险。研究表明，当前 LLM 生成代码中约 **15-25%** 存在潜在安全漏洞 [1]。",
    "\n\n## 2. 主要安全风险类型\n\n| 漏洞类型 | 出现频率 | 严重程度 | 常见场景 |\n|:---|:---|:---|:---|\n| SQL 注入 | 18.3% | 🔴 高 | 数据库查询拼接 |\n| XSS | 12.7% | 🟡 中 | 前端模板渲染 |\n| 路径遍历 | 9.1% | 🔴 高 | 文件操作 |\n| 硬编码密钥 | 15.4% | 🔴 高 | 配置/认证代码 |\n| 不安全反序列化 | 6.2% | 🟡 中 | API 数据处理 |\n\n### 2.1 模型间安全性对比\n\n- **Claude 3.5 Sonnet** 安全拒绝率最高（94%），对危险代码模式识别最敏感 [2]",
    "\n- **GPT-4o** 在提示词注入防御方面表现较好，但偶尔生成未转义的用户输入处理代码\n- **开源模型**（Llama、DeepSeek）安全护栏较弱，需要额外的代码审查流程\n\n## 3. 防御建议\n\n1. **必须进行人工代码审查**：不应直接将 AI 生成代码用于生产环境\n2. **集成 SAST 工具**：如 Semgrep、CodeQL 自动扫描 AI 生成代码 [3]\n3. **使用安全提示词模板**：在 prompt 中明确要求\"使用参数化查询\"\"转义用户输入\"等\n4. **最小权限原则**：限制 AI 代码的文件系统和网络访问范围",
    "\n\n## 4. 结论\n\nAI 代码生成在提高效率的同时引入了系统性安全风险。建议企业建立 **AI 代码安全审查流程**，将自动化扫描工具与人工审查相结合，尤其关注涉及认证、数据库和文件操作的生成代码。\n\n## 参考来源\n\n1. [AI Code Security Analysis Report 2024](https://example.com/security)\n2. [LLM Safety Benchmarks](https://example.com/safety)\n3. [OWASP AI Code Generation Guide](https://example.com/owasp-ai)\n\n---\n\n*本报告根据用户选择「关注安全性」方向生成，由 AutoResearcher 自动撰写。*",
  ],
  "聚焦实际应用案例": [
    "# AI 代码生成实际应用案例研究\n\n## 1. 企业落地现状\n\n本报告基于用户要求，重点收集 AI 代码生成的真实应用案例。截至 2024 年底，全球已有超过 **70%** 的开发者在日常工作中使用 AI 编程助手 [1]。",
    "\n\n## 2. 典型案例分析\n\n### 案例一：Google 内部代码审查\nGoogle 将 AI 应用于代码审查流程，自动检测代码风格问题和潜在 bug。据内部数据，**代码审查时间缩短了 30%**，首次通过率提升 15% [2]。\n\n### 案例二：Shopify 商户工具开发\nShopify 使用 Claude 辅助开发商户管理工具，一个 5 人团队在 3 周内完成了原本预计 2 个月的功能模块。关键收益：\n- 样板代码生成速度提升 **5 倍**\n- 单元测试覆盖率从 45% 提升至 82%\n- 文档编写时间减少 60%",
    "\n\n### 案例三：Stripe 支付 API 迁移\nStripe 利用 AI 辅助完成了一次大规模 API 版本迁移，涉及 **1200+ 个端点**的适配：\n- AI 自动生成 85% 的迁移代码\n- 人工审查发现仅 3% 需要修改\n- 项目提前 2 周交付\n\n### 案例四：初创公司 MVP 加速\n多个 YC 2024 批次的初创公司报告，使用 AI 编程工具后 MVP 开发周期从平均 **8 周缩短至 3 周** [3]。\n\n## 3. 效率提升数据汇总\n\n| 场景 | 效率提升 | 质量影响 |\n|:---|:---|:---|\n| 样板代码 | 5-10x | 无显著影响 |\n| 单元测试 | 3-5x | 覆盖率提升 |\n| Bug 修复 | 2-3x | 需人工验证 |\n| 代码审查 | 1.5-2x | 一致性提升 |",
    "\n\n## 4. 落地建议\n\n1. **从低风险场景开始**：测试代码、文档、内部工具优先\n2. **建立 AI 代码审查流程**：任何 AI 生成代码必须经过人工 review\n3. **度量 ROI**：跟踪 AI 引入前后的开发周期、bug 率、代码覆盖率\n\n## 参考来源\n\n1. [GitHub Developer Survey 2024](https://example.com/survey)\n2. [Google AI-Assisted Code Review](https://example.com/google-ai)\n3. [YC Startup AI Adoption Report](https://example.com/yc-ai)\n\n---\n\n*本报告根据用户选择「聚焦实际应用案例」方向生成，由 AutoResearcher 自动撰写。*",
  ],
};

const DEFAULT_REPORT = [
  "# 大语言模型在代码生成领域的最新进展\n\n## 1. 背景\n\n近年来，大语言模型（LLM）在代码生成任务中取得了显著突破。",
  "从早期的 Codex 到如今的 GPT-4、Claude 3.5 Sonnet 和 Gemini Pro，模型在 HumanEval、MBPP 等基准测试上的通过率已从不足 30% 提升至超过 90% [1]。\n\n",
  "## 2. 主流模型对比\n\n| 模型 | HumanEval | MBPP | 多语言支持 |\n|:---|:---|:---|:---|\n| GPT-4o | 90.2% | 85.7% | 优秀 |\n| Claude 3.5 Sonnet | 92.0% | 87.1% | 优秀 |\n| Gemini Pro | 84.1% | 80.3% | 良好 |\n\n",
  '## 3. 关键发现\n\n- **上下文理解**是当前模型间最大差异点，长上下文窗口的模型在复杂项目级代码生成中优势明显 [2]\n- **安全性**仍是主要挑战：约 15% 的生成代码存在潜在安全漏洞 [3]\n- **多语言能力**差异显著，Python 表现普遍优于其他语言\n\n## 4. 参考来源\n\n1. [HumanEval Benchmark Results 2024](https://example.com/humaneval)\n2. [Long Context Code Generation Study](https://example.com/longctx)\n3. [AI Code Security Analysis Report](https://example.com/security)\n\n---\n\n*本报告由 AutoResearcher 自动生成，请核实关键数据。*',
];

export function createPostFeedbackEvents(feedback: string): Array<{
  event: SSEEvent;
  delay: number;
}> {
  const reportChunks = REPORT_VARIANTS[feedback] ?? DEFAULT_REPORT;

  return [
    {
      delay: 500,
      event: {
        type: "phase_change",
        phase: "writing",
        from_phase: "awaiting_human_input",
        timestamp: ts(13.3),
      },
    },
    ...reportChunks.map((chunk, i) => ({
      delay: i === 0 ? 400 : 300,
      event: {
        type: "report_chunk" as const,
        chunk,
        chunk_index: i,
        is_final: i === reportChunks.length - 1,
      },
    })),
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
