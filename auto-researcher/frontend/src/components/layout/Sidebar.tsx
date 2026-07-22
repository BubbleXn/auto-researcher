"use client";

import { cn } from "@/lib/cn";
import { Plus, History, FlaskConical, PanelLeftClose } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "#", label: "历史记录", icon: History, disabled: true },
];

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

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

      <div className="px-2 mb-1">
        <Link
          href="/"
          className={cn(
            "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-colors",
            pathname === "/"
              ? "bg-surface-700 text-text-primary"
              : "text-text-secondary hover:text-text-primary hover:bg-surface-700"
          )}
        >
          <Plus className="w-4 h-4" />
          新研究
        </Link>
      </div>

      <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              href={item.disabled ? "#" : item.href}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
                "text-text-secondary hover:text-text-primary hover:bg-surface-700",
                item.disabled && "opacity-40 pointer-events-none"
              )}
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-3">
        <p className="text-xs text-text-tertiary text-center">
          AI 生成内容，请核实
        </p>
      </div>
    </aside>
  );
}
