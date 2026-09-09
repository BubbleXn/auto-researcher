"use client";

import type { ConnectionStatus } from "@/types/research";
import { StatusDot } from "@/components/shared/StatusDot";

interface HeaderProps {
  status: ConnectionStatus;
}

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  idle: "",
  connecting: "连接中...",
  connected: "已连接",
  disconnected: "已断开",
  error: "连接错误",
};

export function Header({ status }: HeaderProps) {
  if (status === "idle") return null;

  return (
    <header className="h-10 shrink-0 flex items-center justify-center relative">
      <div className="absolute right-4 flex items-center gap-1.5 text-xs text-text-tertiary">
        <StatusDot status={status} />
        <span>{STATUS_LABELS[status]}</span>
      </div>
    </header>
  );
}
