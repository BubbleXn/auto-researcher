"use client";

import { useState, useRef, useCallback } from "react";
import { ArrowUp } from "lucide-react";
import { cn } from "@/lib/cn";

interface ChatInputProps {
  onSubmit: (query: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSubmit, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="pb-4 pt-2 px-4 no-print">
      <div className="relative max-w-3xl mx-auto">
        <div className="relative rounded-3xl bg-surface-700 border border-surface-500/40 focus-within:border-surface-400/60 transition-colors">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="输入研究问题..."
            rows={1}
            className={cn(
              "w-full resize-none bg-transparent",
              "pl-5 pr-14 py-3.5 text-base text-text-primary placeholder:text-text-tertiary",
              "focus:outline-none",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          />
          <button
            onClick={handleSubmit}
            disabled={!canSend}
            className={cn(
              "absolute right-2.5 bottom-2.5 w-8 h-8 rounded-full flex items-center justify-center transition-colors",
              canSend
                ? "bg-text-primary text-surface-800 hover:opacity-80"
                : "bg-surface-500/50 text-surface-400 cursor-not-allowed"
            )}
          >
            <ArrowUp className="w-4.5 h-4.5" strokeWidth={2.5} />
          </button>
        </div>
        <p className="text-xs text-text-tertiary text-center mt-2">
          AutoResearcher 可能会犯错，请核实重要信息
        </p>
      </div>
    </div>
  );
}
