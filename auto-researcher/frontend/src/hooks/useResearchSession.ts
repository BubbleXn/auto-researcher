"use client";

import { useReducer, useCallback } from "react";
import type { ResearchSession, PhaseState } from "@/types/research";
import type { SSEEvent, ResearchPhase } from "@/types/sse-events";

type SessionAction =
  | { type: "START_RESEARCH"; query: string }
  | { type: "SSE_EVENT"; event: SSEEvent }
  | { type: "SUBMIT_INPUT"; inputId: string; response: string }
  | { type: "SKIP_INPUT"; inputId: string }
  | { type: "CONNECTION_STATUS"; status: ResearchSession["connectionStatus"] }
  | { type: "RESET" };

const INITIAL_STATE: ResearchSession = {
  researchId: null,
  query: "",
  status: "idle",
  connectionStatus: "idle",
  phases: [],
  currentPhase: null,
  reportMarkdown: "",
  reportId: null,
  error: null,
  pendingInput: null,
};

function createPhaseState(phase: ResearchPhase, timestamp: string): PhaseState {
  return {
    phase,
    status: "active",
    steps: [],
    progress: null,
    startedAt: timestamp,
    completedAt: null,
  };
}

function sessionReducer(
  state: ResearchSession,
  action: SessionAction
): ResearchSession {
  switch (action.type) {
    case "START_RESEARCH":
      return {
        ...INITIAL_STATE,
        query: action.query,
        status: "running",
        connectionStatus: "connecting",
      };

    case "CONNECTION_STATUS":
      return { ...state, connectionStatus: action.status };

    case "RESET":
      return INITIAL_STATE;

    case "SSE_EVENT":
      return handleSSEEvent(state, action.event);

    case "SUBMIT_INPUT":
    case "SKIP_INPUT":
      return {
        ...state,
        status: "running",
        pendingInput: null,
      };
  }
}

function handleSSEEvent(
  state: ResearchSession,
  event: SSEEvent
): ResearchSession {
  switch (event.type) {
    case "research_start":
      return {
        ...state,
        researchId: event.research_id,
        connectionStatus: "connected",
      };

    case "phase_change": {
      const phases = state.phases.map((p) =>
        p.phase === event.from_phase
          ? { ...p, status: "completed" as const, completedAt: event.timestamp }
          : p
      );
      return {
        ...state,
        currentPhase: event.phase,
        phases: [...phases, createPhaseState(event.phase, event.timestamp)],
      };
    }

    case "agent_step": {
      const step = {
        stepId: event.step_id,
        action: event.action,
        detail: event.detail,
        timestamp: event.timestamp,
      };
      return {
        ...state,
        phases: state.phases.map((p) =>
          p.phase === event.phase
            ? { ...p, steps: [...p.steps, step] }
            : p
        ),
      };
    }

    case "progress":
      return {
        ...state,
        phases: state.phases.map((p) =>
          p.phase === event.phase
            ? {
                ...p,
                progress: {
                  current: event.current,
                  total: event.total,
                  detail: event.detail,
                },
              }
            : p
        ),
      };

    case "human_input_needed":
      return {
        ...state,
        status: "awaiting_input",
        pendingInput: {
          inputId: event.input_id,
          prompt: event.prompt,
          options: event.options,
        },
      };

    case "report_chunk":
      return {
        ...state,
        reportMarkdown: state.reportMarkdown + event.chunk,
      };

    case "error":
      return {
        ...state,
        status: "error",
        error: {
          errorCode: event.error_code,
          message: event.message,
          recoverable: event.recoverable,
        },
      };

    case "done":
      return {
        ...state,
        status: "completed",
        connectionStatus: "disconnected",
        reportId: event.report_id ?? event.research_id,
        phases: state.phases.map((p) =>
          p.status === "active"
            ? { ...p, status: "completed" as const, completedAt: event.timestamp }
            : p
        ),
        currentPhase: null,
      };
  }
}

export function useResearchSession() {
  const [session, dispatch] = useReducer(sessionReducer, INITIAL_STATE);

  const startResearch = useCallback((query: string) => {
    dispatch({ type: "START_RESEARCH", query });
  }, []);

  const handleSSEEvent = useCallback((event: SSEEvent) => {
    dispatch({ type: "SSE_EVENT", event });
  }, []);

  const submitInput = useCallback((inputId: string, response: string) => {
    dispatch({ type: "SUBMIT_INPUT", inputId, response });
  }, []);

  const skipInput = useCallback((inputId: string) => {
    dispatch({ type: "SKIP_INPUT", inputId });
  }, []);

  const setConnectionStatus = useCallback(
    (status: ResearchSession["connectionStatus"]) => {
      dispatch({ type: "CONNECTION_STATUS", status });
    },
    []
  );

  const reset = useCallback(() => {
    dispatch({ type: "RESET" });
  }, []);

  return {
    session,
    startResearch,
    handleSSEEvent,
    submitInput,
    skipInput,
    setConnectionStatus,
    reset,
  };
}
