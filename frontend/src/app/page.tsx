"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { ChatInput } from "@/components/chat/ChatInput";
import { ThinkingChain } from "@/components/chat/ThinkingChain";
import { HumanInputPrompt } from "@/components/chat/HumanInputPrompt";
import { ReportView } from "@/components/report/ReportView";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { Spinner } from "@/components/shared/Spinner";
import { useResearchSession } from "@/hooks/useResearchSession";
import { useSSE } from "@/hooks/useSSE";
import { SSE_ENDPOINT, HUMAN_INPUT_ENDPOINT } from "@/lib/constants";

export default function HomePage() {
  const {
    session,
    startResearch,
    handleSSEEvent,
    submitInput,
    skipInput,
    setConnectionStatus,
    reset,
  } = useResearchSession();

  const { connect } = useSSE(SSE_ENDPOINT, {
    onEvent: handleSSEEvent,
    onStatusChange: setConnectionStatus,
    researchId: session.researchId,
  });

  const handleSubmit = (query: string) => {
    startResearch(query);
    connect({ query });
  };

  const handleRetry = () => {
    if (session.query) {
      reset();
      handleSubmit(session.query);
    }
  };

  const isRunning =
    session.status === "running" || session.status === "awaiting_input";

  return (
    <AppShell>
      <Header status={session.connectionStatus} />

      <div className="flex-1 overflow-y-auto">
        {session.status === "idle" ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <h1 className="text-2xl font-semibold text-text-primary mb-2">
              有什么想研究的？
            </h1>
            <p className="text-text-tertiary max-w-md">
              输入一个研究问题，AI 将自动规划、检索、验证并生成研究报告
            </p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4">
            {session.query && (
              <div className="pt-8 pb-4">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-surface-500 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-xs font-medium text-text-primary">你</span>
                  </div>
                  <p className="text-text-primary pt-1">{session.query}</p>
                </div>
              </div>
            )}

            {session.error && (
              <ErrorBanner
                error={{
                  type: "error",
                  error_code: session.error.errorCode,
                  message: session.error.message,
                  recoverable: session.error.recoverable,
                }}
                onRetry={session.error.recoverable ? handleRetry : undefined}
                onDismiss={() => reset()}
              />
            )}

            <ThinkingChain
              phases={session.phases}
              currentPhase={session.currentPhase}
            />

            {isRunning && session.phases.length === 0 && (
              <div className="flex items-center gap-3 py-4">
                <Spinner size="md" />
                <span className="text-text-secondary">正在分析您的问题...</span>
              </div>
            )}

            {isRunning && session.currentPhase === "writing" && !session.reportMarkdown && (
              <div className="flex items-center gap-3 py-4 px-1">
                <Spinner size="md" />
                <span className="text-text-secondary">正在生成研究报告，请稍候...</span>
              </div>
            )}

            {session.pendingInput && (
              <HumanInputPrompt
                prompt={session.pendingInput.prompt}
                options={session.pendingInput.options}
                outline={session.pendingInput.outline}
                onSubmit={(response) => {
                  const inputId = session.pendingInput!.inputId;
                  submitInput(inputId, response);
                  fetch(HUMAN_INPUT_ENDPOINT, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      research_id: session.researchId,
                      input_id: inputId,
                      feedback: response,
                    }),
                  }).catch(console.error);
                }}
                onSkip={() => {
                  const inputId = session.pendingInput!.inputId;
                  skipInput(inputId);
                  fetch(HUMAN_INPUT_ENDPOINT, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      research_id: session.researchId,
                      input_id: inputId,
                      feedback: "",
                    }),
                  }).catch(console.error);
                }}
              />
            )}

            {session.reportMarkdown && (
              <ReportView markdown={session.reportMarkdown} />
            )}
          </div>
        )}
      </div>

      <ChatInput onSubmit={handleSubmit} disabled={isRunning} />
    </AppShell>
  );
}
