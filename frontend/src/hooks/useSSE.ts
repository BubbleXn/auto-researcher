"use client";

import { useRef, useCallback, useEffect } from "react";
import type { SSEEvent } from "@/types/sse-events";
import type { ConnectionStatus } from "@/types/research";

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

interface UseSSEOptions {
  onEvent: (event: SSEEvent) => void;
  onStatusChange: (status: ConnectionStatus) => void;
  researchId?: string | null;
}

export function useSSE(url: string, { onEvent, onStatusChange, researchId }: UseSSEOptions) {
  const abortRef = useRef<AbortController | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectInternalRef = useRef<
    ((body: Record<string, unknown>, isReconnect: boolean) => Promise<void>) | null
  >(null);
  const lastEventIdRef = useRef<string | null>(null);
  const researchIdRef = useRef<string | null>(null);
  const retryCountRef = useRef(0);
  const lastBodyRef = useRef<Record<string, unknown> | null>(null);

  useEffect(() => {
    researchIdRef.current = researchId ?? null;
  }, [researchId]);

  const connectInternal = useCallback(
    async (body: Record<string, unknown>, isReconnect: boolean) => {
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      onStatusChange("connecting");

      const canResume = isReconnect && lastEventIdRef.current && researchIdRef.current;
      const requestBody = canResume
        ? {
            ...body,
            research_id: researchIdRef.current,
            resume_from_event_id: Number(lastEventIdRef.current),
          }
        : body;

      const scheduleRetry = () => {
        if (retryCountRef.current < MAX_RETRIES && lastBodyRef.current) {
          retryCountRef.current++;
          const delay = BASE_DELAY_MS * Math.pow(2, retryCountRef.current - 1);
          reconnectTimerRef.current = setTimeout(() => {
            reconnectTimerRef.current = null;
            if (lastBodyRef.current) {
              void connectInternalRef.current?.(lastBodyRef.current, true);
            }
          }, delay);
        } else {
          onStatusChange("error");
        }
      };

      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(requestBody),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          // Retry transient server failures; client errors (4xx) are fatal.
          if (res.status >= 500 || res.status === 429) {
            scheduleRetry();
          } else {
            onStatusChange("error");
          }
          return;
        }

        onStatusChange("connected");
        retryCountRef.current = 0;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const lines = part.split("\n");
            const eventLine = lines.find((l) => l.startsWith("event: "));
            const dataLine = lines.find((l) => l.startsWith("data: "));
            if (!dataLine) continue;

            try {
              const parsed = JSON.parse(dataLine.slice(6));
              if (eventLine && !parsed.type) {
                parsed.type = eventLine.slice(7);
              }
              const event = parsed as SSEEvent;
              if (event.event_id) {
                lastEventIdRef.current = String(event.event_id);
              }
              onEvent(event);
            } catch {
              // skip malformed events
            }
          }
        }

        onStatusChange("disconnected");
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          onStatusChange("disconnected");
          return;
        }
        scheduleRetry();
      }
    },
    [url, onEvent, onStatusChange]
  );

  // Keep a ref to the latest connectInternal so scheduled retries can call
  // it without the callback referencing its own variable before declaration.
  useEffect(() => {
    connectInternalRef.current = connectInternal;
  }, [connectInternal]);

  const connect = useCallback(
    async (body: Record<string, unknown>) => {
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      lastBodyRef.current = body;
      lastEventIdRef.current = null;
      retryCountRef.current = 0;
      await connectInternal(body, false);
    },
    [connectInternal]
  );

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    abortRef.current?.abort();
    abortRef.current = null;
    lastBodyRef.current = null;
    lastEventIdRef.current = null;
    retryCountRef.current = 0;
  }, []);

  return { connect, disconnect };
}
