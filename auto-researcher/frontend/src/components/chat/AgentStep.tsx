import type { AgentStepData } from "@/types/research";
import {
  ListChecks,
  Search,
  CheckCircle2,
  FileText,
  AlertTriangle,
  RefreshCw,
  PenLine,
} from "lucide-react";
import { cn } from "@/lib/cn";

const ACTION_ICONS: Record<string, React.ReactNode> = {
  plan_created: <ListChecks className="w-3.5 h-3.5 text-phase-planning" />,
  decompose: <ListChecks className="w-3.5 h-3.5 text-phase-planning" />,
  outline: <ListChecks className="w-3.5 h-3.5 text-phase-planning" />,
  search_started: <Search className="w-3.5 h-3.5 text-phase-searching" />,
  search_completed: <CheckCircle2 className="w-3.5 h-3.5 text-phase-searching" />,
  web_search: <Search className="w-3.5 h-3.5 text-phase-searching" />,
  pdf_parsed: <FileText className="w-3.5 h-3.5 text-phase-searching" />,
  conflict_detected: <AlertTriangle className="w-3.5 h-3.5 text-status-warning" />,
  conflict_check: <AlertTriangle className="w-3.5 h-3.5 text-status-warning" />,
  verify: <CheckCircle2 className="w-3.5 h-3.5 text-phase-critiquing" />,
  retry_triggered: <RefreshCw className="w-3.5 h-3.5 text-status-warning" />,
  writing_report: <PenLine className="w-3.5 h-3.5 text-phase-writing" />,
};

export function AgentStep({ step }: { step: AgentStepData }) {
  const icon = ACTION_ICONS[step.action] || (
    <div className="w-3.5 h-3.5 rounded-full bg-surface-500/60" />
  );

  return (
    <div className="flex items-start gap-2 py-0.5 text-sm animate-in">
      <span className="text-text-tertiary font-mono shrink-0 tabular-nums text-xs mt-0.5">
        {new Date(step.timestamp).toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}
      </span>
      <span className="shrink-0 mt-0.5">{icon}</span>
      <span className="text-text-secondary text-sm">{step.detail}</span>
    </div>
  );
}
