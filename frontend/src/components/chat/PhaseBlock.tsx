"use client";

import { useState } from "react";
import type { PhaseState } from "@/types/research";
import { PHASE_LABELS, PHASE_COLORS } from "@/lib/constants";
import { AgentStep } from "./AgentStep";
import { ProgressBar } from "./ProgressBar";
import { Spinner } from "@/components/shared/Spinner";
import { ChevronDown, Check, Pause } from "lucide-react";
import { cn } from "@/lib/cn";

interface PhaseBlockProps {
  phase: PhaseState;
  isLast: boolean;
  isCurrent: boolean;
}

export function PhaseBlock({ phase, isCurrent }: PhaseBlockProps) {
  const [expanded, setExpanded] = useState(true);
  const colorClass = PHASE_COLORS[phase.phase];

  return (
    <div className="mb-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex items-center gap-2 py-1.5 w-full text-left",
          "text-sm transition-colors group",
          isCurrent ? "text-text-primary" : "text-text-secondary"
        )}
      >
        {phase.status === "active" ? (
          phase.phase === "awaiting_human_input" ? (
            <Pause className={cn("w-4 h-4", colorClass)} />
          ) : (
            <Spinner size="sm" className={cn("!text-current", colorClass)} />
          )
        ) : phase.status === "completed" ? (
          <Check className={cn("w-4 h-4", colorClass)} />
        ) : (
          <div className="w-4 h-4 rounded-full bg-surface-500" />
        )}
        <span className={colorClass}>{PHASE_LABELS[phase.phase]}</span>
        {phase.steps.length > 0 && (
          <span className="text-xs text-text-tertiary">
            {phase.steps.length} 步
          </span>
        )}
        <ChevronDown
          className={cn(
            "w-3.5 h-3.5 ml-auto text-text-tertiary transition-transform opacity-0 group-hover:opacity-100",
            expanded && "rotate-180"
          )}
        />
      </button>

      {expanded && (
        <div className="pl-6 pb-2 space-y-0.5">
          {phase.progress && <ProgressBar {...phase.progress} />}
          {phase.steps.map((step) => (
            <AgentStep key={step.stepId} step={step} />
          ))}
          {phase.status === "active" && phase.steps.length === 0 && (
            <div className="flex items-center gap-2 py-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-pulse" />
              <p className="text-sm text-text-secondary">
                {phase.phase === "writing" ? "正在生成报告..." : "处理中..."}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
