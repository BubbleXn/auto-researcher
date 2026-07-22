import type { PhaseState } from "@/types/research";
import type { ResearchPhase } from "@/types/sse-events";
import { PhaseBlock } from "./PhaseBlock";

interface ThinkingChainProps {
  phases: PhaseState[];
  currentPhase: ResearchPhase | null;
}

export function ThinkingChain({ phases, currentPhase }: ThinkingChainProps) {
  if (phases.length === 0) return null;

  return (
    <div className="py-4 space-y-2">
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-full bg-surface-900 flex items-center justify-center shrink-0 mt-0.5 border border-surface-500/40">
          <span className="text-xs font-medium text-phase-searching">R</span>
        </div>
        <div className="flex-1 min-w-0">
          {phases.map((phase, i) => (
            <PhaseBlock
              key={phase.phase}
              phase={phase}
              isLast={i === phases.length - 1}
              isCurrent={phase.phase === currentPhase}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
