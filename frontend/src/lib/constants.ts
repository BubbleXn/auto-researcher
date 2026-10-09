import type { ResearchPhase } from "@/types/sse-events";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const SSE_ENDPOINT = `${API_BASE_URL}/api/research/start`;
export const HUMAN_INPUT_ENDPOINT = `${API_BASE_URL}/api/research/feedback`;
export const HISTORY_ENDPOINT = `${API_BASE_URL}/api/research/history`;
export const reportDetailUrl = (researchId: string) =>
  `${API_BASE_URL}/api/research/history/${researchId}/report`;

export const PHASE_LABELS: Record<ResearchPhase, string> = {
  planning: "规划研究方案",
  searching: "检索信息",
  critiquing: "验证与审核",
  awaiting_human_input: "等待确认",
  writing: "生成报告",
  completed: "已完成",
  error: "出现问题",
};

export const PHASE_COLORS: Record<ResearchPhase, string> = {
  planning: "phase-planning",
  searching: "phase-searching",
  critiquing: "phase-critiquing",
  awaiting_human_input: "phase-critiquing",
  writing: "phase-writing",
  completed: "phase-writing",
  error: "phase-critiquing",
};

export const PHASE_BG_COLORS: Record<ResearchPhase, string> = {
  planning: "bg-phase-planning",
  searching: "bg-phase-searching",
  critiquing: "bg-phase-critiquing",
  awaiting_human_input: "bg-phase-critiquing",
  writing: "bg-phase-writing",
  completed: "bg-phase-writing",
  error: "bg-phase-critiquing",
};
