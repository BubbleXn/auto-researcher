"use client";

import { useState } from "react";
import { MessageSquare, SkipForward, ArrowUp } from "lucide-react";
import { cn } from "@/lib/cn";

interface HumanInputPromptProps {
  prompt: string;
  options?: string[];
  onSubmit: (response: string) => void;
  onSkip: () => void;
}

export function HumanInputPrompt({
  prompt,
  options,
  onSubmit,
  onSkip,
}: HumanInputPromptProps) {
  const [response, setResponse] = useState("");

  const handleSubmit = () => {
    const trimmed = response.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setResponse("");
  };

  return (
    <div className="my-4 p-4 rounded-2xl bg-surface-700/60 border border-surface-500/30">
      <div className="flex items-start gap-2.5 mb-3">
        <MessageSquare className="w-4 h-4 text-status-warning shrink-0 mt-0.5" />
        <p className="text-sm text-text-primary leading-relaxed">{prompt}</p>
      </div>

      {options && options.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3 pl-6">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => onSubmit(opt)}
              className="px-3 py-1.5 text-sm rounded-full bg-surface-700 text-text-secondary hover:text-text-primary hover:bg-surface-600 border border-surface-500/40 transition-colors"
            >
              {opt}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 pl-6">
        <input
          type="text"
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="输入补充说明..."
          className={cn(
            "flex-1 px-3.5 py-2 text-sm rounded-xl bg-surface-700",
            "border border-surface-500/40 text-text-primary placeholder:text-text-tertiary",
            "focus:outline-none focus:border-surface-400/60"
          )}
        />
        <button
          onClick={handleSubmit}
          disabled={!response.trim()}
          className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center transition-colors",
            response.trim()
              ? "bg-text-primary text-surface-800 hover:opacity-80"
              : "bg-surface-500/50 text-surface-400 cursor-not-allowed"
          )}
        >
          <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
        </button>
        <button
          onClick={onSkip}
          className="p-2 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-surface-600 transition-colors"
          title="跳过"
        >
          <SkipForward className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
