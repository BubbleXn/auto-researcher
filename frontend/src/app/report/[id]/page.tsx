"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { ReportView } from "@/components/report/ReportView";
import { Spinner } from "@/components/shared/Spinner";
import { AlertTriangle } from "lucide-react";
import { reportDetailUrl } from "@/lib/constants";
import type { ReportDetail } from "@/types/research";

type ReportPageState = {
  status: "loading" | "ready" | "not_found" | "error";
  detail: ReportDetail | null;
};

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const researchId = params?.id;
  const [state, setState] = useState<ReportPageState>({
    status: "loading",
    detail: null,
  });

  useEffect(() => {
    if (!researchId) return;
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(reportDetailUrl(researchId));
        if (res.status === 404) {
          if (!cancelled) setState({ status: "not_found", detail: null });
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const detail = (await res.json()) as ReportDetail;
        if (!cancelled) setState({ status: "ready", detail });
      } catch {
        if (!cancelled) setState({ status: "error", detail: null });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [researchId]);

  // Derive staleness at render time instead of resetting state inside the
  // effect: navigating between reports reuses this component instance, so a
  // detail from the previous id must show as loading until the new one lands.
  const isStale =
    state.detail !== null && state.detail.research_id !== researchId;
  const showLoading = state.status === "loading" || isStale;

  return (
    <AppShell>
      <Header status="idle" />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 pt-6 pb-10">
          {showLoading && (
            <div className="flex items-center justify-center gap-3 py-24">
              <Spinner size="md" />
              <span className="text-text-secondary text-sm">
                正在加载报告...
              </span>
            </div>
          )}

          {state.status === "not_found" && (
            <div className="flex flex-col items-center gap-3 py-24 text-center">
              <AlertTriangle className="w-8 h-8 text-status-warning" />
              <p className="text-text-primary">报告不存在或尚未生成</p>
              <p className="text-xs text-text-tertiary font-mono">
                ID: {researchId}
              </p>
              <Link
                href="/"
                className="text-sm text-link hover:underline mt-2"
              >
                ← 返回发起新研究
              </Link>
            </div>
          )}

          {state.status === "error" && (
            <div className="flex flex-col items-center gap-3 py-24 text-center">
              <AlertTriangle className="w-8 h-8 text-status-warning" />
              <p className="text-text-primary">报告加载失败，请稍后重试</p>
              <Link
                href="/"
                className="text-sm text-link hover:underline mt-2"
              >
                ← 返回首页
              </Link>
            </div>
          )}

          {state.status === "ready" && state.detail && (
            <>
              <div className="mb-2">
                <Link
                  href="/"
                  className="text-xs text-text-tertiary hover:text-text-secondary"
                >
                  ← 新研究
                </Link>
              </div>
              <p className="text-xs text-text-tertiary font-mono mb-1">
                报告 ID: {state.detail.research_id}
              </p>
              <h1 className="text-lg font-semibold text-text-primary mb-1">
                {state.detail.query}
              </h1>
              <p className="text-xs text-text-tertiary mb-4">
                {new Date(state.detail.created_at).toLocaleString("zh-CN")} ·{" "}
                {state.detail.total_sources} 个来源 · 耗时{" "}
                {state.detail.duration_seconds.toFixed(1)}s
              </p>
              <ReportView markdown={state.detail.report_markdown} />
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
