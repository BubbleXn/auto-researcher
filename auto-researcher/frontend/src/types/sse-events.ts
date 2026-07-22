export type ResearchPhase = "planning" | "searching" | "critiquing" | "awaiting_human_input" | "writing";

export type SSEEventType =
  | "research_start"
  | "phase_change"
  | "agent_step"
  | "progress"
  | "human_input_needed"
  | "report_chunk"
  | "error"
  | "done";

interface SSEEventBase {
  event_id?: string | number;
}

export interface ResearchStartEvent extends SSEEventBase {
  type: "research_start";
  research_id: string;
  query: string;
  timestamp: string;
}

export interface PhaseChangeEvent extends SSEEventBase {
  type: "phase_change";
  phase: ResearchPhase;
  from_phase: ResearchPhase | null;
  message?: string;
  timestamp: string;
}

export interface AgentStepEvent extends SSEEventBase {
  type: "agent_step";
  phase: ResearchPhase;
  step_id: string;
  action: string;
  detail: string;
  node?: string;
  timestamp: string;
}

export interface ProgressEvent extends SSEEventBase {
  type: "progress";
  phase: ResearchPhase;
  current: number;
  total: number;
  detail: string;
}

export interface HumanInputNeededEvent extends SSEEventBase {
  type: "human_input_needed";
  phase?: ResearchPhase;
  prompt: string;
  input_id: string;
  options?: string[];
  outline?: Array<{ section: string; key_points?: string[] }>;
  editable_fields?: string[];
}

export interface ReportChunkEvent extends SSEEventBase {
  type: "report_chunk";
  chunk: string;
  chunk_index: number;
  is_final: boolean;
}

export interface SSEErrorEvent extends SSEEventBase {
  type: "error";
  error_code: string;
  message: string;
  recoverable: boolean;
  phase?: ResearchPhase;
}

export interface DoneEvent extends SSEEventBase {
  type: "done";
  research_id: string;
  report_id?: string;
  total_sources?: number;
  total_duration_seconds: number;
  timestamp: string;
}

export type SSEEvent =
  | ResearchStartEvent
  | PhaseChangeEvent
  | AgentStepEvent
  | ProgressEvent
  | HumanInputNeededEvent
  | ReportChunkEvent
  | SSEErrorEvent
  | DoneEvent;
