import type { ConnectionStatus } from "@/types/research";
import { cn } from "@/lib/cn";

const STATUS_STYLES: Record<ConnectionStatus, string> = {
  idle: "bg-text-tertiary",
  connecting: "bg-status-warning animate-pulse",
  connected: "bg-status-success",
  disconnected: "bg-text-tertiary",
  error: "bg-status-error animate-pulse",
};

export function StatusDot({ status }: { status: ConnectionStatus }) {
  return (
    <span className={cn("inline-block w-2 h-2 rounded-full", STATUS_STYLES[status])} />
  );
}
