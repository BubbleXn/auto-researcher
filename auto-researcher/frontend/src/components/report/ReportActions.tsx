"use client";

import { useState } from "react";
import { Copy, Check, Printer } from "lucide-react";

interface ReportActionsProps {
  markdown: string;
}

export function ReportActions({ markdown }: ReportActionsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-2 mb-4 no-print">
      <button
        onClick={handleCopy}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-surface-700 text-text-secondary hover:text-text-primary border border-surface-500/30 transition-colors"
      >
        {copied ? (
          <Check className="w-4 h-4 text-status-success" />
        ) : (
          <Copy className="w-4 h-4" />
        )}
        {copied ? "已复制" : "复制"}
      </button>
      <button
        onClick={() => window.print()}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-surface-700 text-text-secondary hover:text-text-primary border border-surface-500/30 transition-colors"
      >
        <Printer className="w-4 h-4" />
        打印
      </button>
    </div>
  );
}
