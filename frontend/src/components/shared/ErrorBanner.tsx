import type { SSEErrorEvent } from "@/types/sse-events";
import { AlertTriangle, RefreshCw, X } from "lucide-react";

interface ErrorBannerProps {
  error: SSEErrorEvent;
  onDismiss?: () => void;
  onRetry?: () => void;
}

export function ErrorBanner({ error, onDismiss, onRetry }: ErrorBannerProps) {
  return (
    <div className="my-3 px-4 py-3 rounded-xl bg-status-error/10 border border-status-error/20 flex items-start gap-3">
      <AlertTriangle className="w-4 h-4 text-status-error shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary">{error.message}</p>
        <p className="text-xs text-text-tertiary mt-1">
          {error.error_code}
        </p>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {error.recoverable && onRetry && (
          <button
            onClick={onRetry}
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
