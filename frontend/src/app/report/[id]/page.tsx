import { ReportView } from "@/components/report/ReportView";
import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";

const PLACEHOLDER_REPORT = `# 研究报告

> 该页面将展示完成的研究报告。报告 ID 将用于从后端获取已保存的报告内容。

## 功能说明

- Markdown 渲染与语法高亮
- 引用来源标注
- 一键复制 Markdown 原文
- 浏览器打印导出 PDF

---

*报告功能将在 Week 3 接入真实数据后完整可用。*
`;

export default async function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <AppShell>
      <Header status="idle" />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 pt-6">
          <p className="text-xs text-text-tertiary font-mono mb-4">
            报告 ID: {id}
          </p>
        </div>
        <ReportView markdown={PLACEHOLDER_REPORT} />
      </div>
    </AppShell>
  );
}
