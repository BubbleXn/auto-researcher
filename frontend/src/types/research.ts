import type { InputOption, ResearchPhase } from "./sse-events";

export type { InputOption };

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

export interface AgentStepData {
  stepId: string;
  action: string;
  detail: string;
  timestamp: string;
}

export interface ProgressData {
  current: number;
  total: number;
  detail: string;
}

export interface PhaseState {
  phase: ResearchPhase;
  status: "pending" | "active" | "completed";
  steps: AgentStepData[];
  progress: ProgressData | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface PendingInput {
  inputId: string;
  prompt: string;
  options?: InputOption[];
  outline?: Array<{ section: string; key_points?: string[] }>;
}

export interface ResearchSession {
  researchId: string | null;
  query: string;
  status: "idle" | "running" | "awaiting_input" | "completed" | "error";
  connectionStatus: ConnectionStatus;
  phases: PhaseState[];
  currentPhase: ResearchPhase | null;
  reportMarkdown: string;
  reportId: string | null;
  error: {
    errorCode: string;
    message: string;
    recoverable: boolean;
  } | null;
  pendingInput: PendingInput | null;
}

export interface Citation {
  index: number;
  url: string;
  title: string;
  domain: string;
}

export interface HistoryItem {
  research_id: string;
  query: string;
  total_sources: number;
  duration_seconds: number;
  created_at: string;
}

export interface ReportDetail {
  research_id: string;
  query: string;
  report_markdown: string;
  sources: Array<{ title?: string; url?: string; [key: string]: unknown }>;
  total_sources: number;
  duration_seconds: number;
  created_at: string;
}
