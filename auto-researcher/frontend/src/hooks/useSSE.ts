"use client";

import { useRef, useCallback } from "react";
import type { SSEEvent } from "@/types/sse-events";
import type { ConnectionStatus } from "@/types/research";

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

interface UseSSEOptions {
  onEvent: (event: SSEEvent) => void;
  onStatusChange: (status: ConnectionStatus) => void;
}

export function useSSE(url: string, { onEvent, onStatusChange }: UseSSEOptions) {
  const abortRef = useRef<AbortController | null>(null);
  const lastEventIdRef = useRef<string | null>(null);
  const retryCountRef = useRef(0);
  const lastBodyRef = useRef<Record<string, unknown> | null>(null);

  const connectInternal = useCallback(
    async (body: Record<string, unknown>, isReconnect: boolean) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      onStatusChange(isReconnect ? "connecting" : "connecting");

      const requestBody = isReconnect && lastEventIdRef.current
        ? { ...body, resume_from_event_id: lastEventIdRef.current }
        : body;

      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(requestBody),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          onStatusChange("error");
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

        if (retryCountRef.current < MAX_RETRIES && lastBodyRef.current) {
          retryCountRef.current++;
          const delay = BASE_DELAY_MS * Math.pow(2, retryCountRef.current - 1);
          setTimeout(() => {
            if (lastBodyRef.current) {
              connectInternal(lastBodyRef.current, true);
            }
          }, delay);
        } else {
          onStatusChange("error");
        }
      }
    },
    [url, onEvent, onStatusChange]
  );

  const connect = useCallback(
    async (body: Record<string, unknown>) => {
      lastBodyRef.current = body;
      lastEventIdRef.current = null;
      retryCountRef.current = 0;
      await connectInternal(body, false);
    },
    [connectInternal]
  );

  const disconnect = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    lastBodyRef.current = null;
    retryCountRef.current = 0;
  }, []);

  return { connect, disconnect };
}
