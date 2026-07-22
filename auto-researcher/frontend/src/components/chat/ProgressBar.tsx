import type { ProgressData } from "@/types/research";

export function ProgressBar({ current, total, detail }: ProgressData) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="py-1">
      <div className="flex items-center gap-2 text-xs mb-1.5">
        <span className="text-text-secondary tabular-nums">
          {current}/{total}
        </span>
        <span className="text-text-tertiary">{detail}</span>
      </div>
      <div className="h-1 bg-surface-600 rounded-full overflow-hidden">
        <div
          className="h-full bg-text-secondary rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
