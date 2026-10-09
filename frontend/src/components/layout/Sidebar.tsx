"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { HISTORY_ENDPOINT } from "@/lib/constants";
import type { HistoryItem } from "@/types/research";
import {
  Plus,
  History,
  FlaskConical,
  PanelLeftClose,
  FileText,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
  /** When provided, "新研究" resets the session instead of a no-op link. */
  onNewResearch?: () => void;
  /** Changing this value (e.g. a finished reportId) reloads the history list. */
  refreshKey?: string | null;
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffMs = Date.now() - then;
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  return new Date(then).toLocaleDateString("zh-CN");
}

export function Sidebar({
  collapsed,
  onToggle,
  onNewResearch,
  refreshKey,
}: SidebarProps) {
  const pathname = usePathname();
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(HISTORY_ENDPOINT);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { items?: HistoryItem[] };
        if (!cancelled) setHistoryItems(data.items ?? []);
      } catch {
        // History is a convenience view; stay silent on backend hiccups.
        if (!cancelled) setHistoryItems([]);
      } finally {
        if (!cancelled) setIsLoadingHistory(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const handleNewResearch = () => {
    if (onNewResearch) {
      onNewResearch();
      return;
    }
  };

  const newResearchClass = cn(
    "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-colors w-full",
    pathname === "/"
      ? "bg-surface-700 text-text-primary"
      : "text-text-secondary hover:text-text-primary hover:bg-surface-700"
  );

  if (collapsed) return null;

  return (
    <aside className="w-[260px] shrink-0 bg-surface-900 flex flex-col">
      <div className="p-2 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 px-2 py-1.5">
          <FlaskConical className="w-5 h-5 text-text-secondary" />
          <span className="font-semibold text-sm text-text-primary">
            AutoResearcher
          </span>
        </Link>
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-surface-700 transition-colors"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="px-2 mb-3">
        {onNewResearch ? (
          <button onClick={handleNewResearch} className={newResearchClass}>
            <Plus className="w-4 h-4" />
            新研究
          </button>
        ) : (
          <Link href="/" className={newResearchClass}>
            <Plus className="w-4 h-4" />
            新研究
          </Link>
        )}
      </div>

      <p className="px-4 pb-1 text-xs font-medium text-text-tertiary flex items-center gap-1.5">
        <History className="w-3.5 h-3.5" />
        历史记录
      </p>
      <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto">
        {isLoadingHistory ? (
          <p className="px-3 py-2 text-xs text-text-tertiary">加载中...</p>
        ) : historyItems.length === 0 ? (
          <p className="px-3 py-2 text-xs text-text-tertiary">
            暂无历史记录
          </p>
        ) : (
          historyItems.map((item) => {
            const href = `/report/${item.research_id}`;
            const isActive = pathname === href;
            return (
              <Link
                key={item.research_id}
                href={href}
                title={item.query}
                className={cn(
                  "flex flex-col gap-0.5 px-3 py-2 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-surface-700 text-text-primary"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-700"
                )}
              >
                <span className="flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 shrink-0 opacity-60" />
                  <span className="truncate">{item.query}</span>
                </span>
                <span className="pl-5.5 text-xs text-text-tertiary">
                  {formatRelativeTime(item.created_at)} · {item.total_sources} 个来源
                </span>
              </Link>
            );
          })
        )}
      </nav>

      <div className="p-3">
        <p className="text-xs text-text-tertiary text-center">
          AI 生成内容，请核实
        </p>
      </div>
    </aside>
  );
}
