import type { ResearchPhase } from "./sse-events";

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
  pendingInput: {
    inputId: string;
    prompt: string;
    options?: string[];
  } | null;
}

export interface Citation {
  index: number;
  url: string;
  title: string;
  domain: string;
}
