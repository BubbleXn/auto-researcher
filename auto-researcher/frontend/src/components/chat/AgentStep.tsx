import type { AgentStepData } from "@/types/research";

export function AgentStep({ step }: { step: AgentStepData }) {
  return (
    <div className="flex items-start gap-2 py-0.5 text-sm">
      <span className="text-text-tertiary font-mono shrink-0 tabular-nums text-xs mt-0.5">
        {new Date(step.timestamp).toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}
      </span>
      <span className="text-link font-medium shrink-0 text-xs mt-0.5">{step.action}</span>
      <span className="text-text-secondary text-sm">{step.detail}</span>
    </div>
  );
}
