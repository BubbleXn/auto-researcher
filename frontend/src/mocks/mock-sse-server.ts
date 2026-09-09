import { createServer } from "node:http";
import { createPreFeedbackEvents, createPostFeedbackEvents } from "./mock-data";

const PORT = 8000;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const SSE_HEADERS = {
  ...CORS_HEADERS,
  "Content-Type": "text/event-stream",
  "Cache-Control": "no-cache",
  Connection: "keep-alive",
};

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let feedbackResolve: ((feedback: string) => void) | null = null;

function waitForFeedback(): Promise<string> {
  return new Promise((resolve) => {
    feedbackResolve = resolve;
  });
}

function readBody(req: import("node:http").IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    let body = "";
    req.on("data", (chunk: Buffer) => { body += chunk; });
    req.on("end", () => resolve(body));
  });
}

const server = createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS_HEADERS);
    res.end();
    return;
  }

  if (req.method === "POST" && req.url?.startsWith("/api/research/feedback")) {
    const body = await readBody(req);
    let feedback = "";
    try {
      feedback = JSON.parse(body).feedback ?? "";
    } catch {}
    console.log(`  ← Feedback received: "${feedback}"`);

    res.writeHead(200, { ...CORS_HEADERS, "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));

    if (feedbackResolve) {
      feedbackResolve(feedback);
      feedbackResolve = null;
    }
    return;
  }

  if (req.method === "POST" && req.url?.startsWith("/api/research/input")) {
    const body = await readBody(req);
    let feedback = "";
    try {
      feedback = JSON.parse(body).feedback ?? JSON.parse(body).response ?? "";
    } catch {}

    res.writeHead(200, { ...CORS_HEADERS, "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));

    if (feedbackResolve) {
      feedbackResolve(feedback);
      feedbackResolve = null;
    }
    return;
  }

  if (req.method === "POST" && req.url?.startsWith("/api/research")) {
    res.writeHead(200, SSE_HEADERS);

    const speed = new URL(
      req.url,
      `http://localhost:${PORT}`
    ).searchParams.get("speed");
    const multiplier = speed === "fast" ? 0.3 : speed === "slow" ? 2 : 1;

    let aborted = false;

    req.on("close", () => {
      aborted = true;
      if (feedbackResolve) {
        feedbackResolve("");
        feedbackResolve = null;
      }
    });

    // Phase 1: pre-feedback events
    const preFeedback = createPreFeedbackEvents();
    for (const { event, delay } of preFeedback) {
      if (aborted) break;
      await sleep(delay * multiplier);
      if (aborted) break;

      const sseData = `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
      res.write(sseData);
    }

    if (aborted) { res.end(); return; }

    // Wait for human feedback
    console.log("  ⏸  Waiting for human feedback...");
    const feedback = await waitForFeedback();
    console.log(`  ▶  User chose: "${feedback}", resuming stream`);

    if (aborted) { res.end(); return; }

    // Phase 2: post-feedback events (report content varies by feedback)
    const postFeedback = createPostFeedbackEvents(feedback);
    for (const { event, delay } of postFeedback) {
      if (aborted) break;
      await sleep(delay * multiplier);
      if (aborted) break;

      const sseData = `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
      res.write(sseData);
    }

    res.end();
    return;
  }

  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", service: "mock-sse" }));
    return;
  }

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("Not Found");
});

server.listen(PORT, () => {
  console.log(`Mock SSE server running at http://localhost:${PORT}`);
  console.log(`  POST /api/research          → SSE event stream`);
  console.log(`  POST /api/research/feedback  → human feedback (resumes stream)`);
  console.log(`  GET  /health                → health check`);
  console.log(`\nFeedback → report mapping:`);
  console.log(`  "深入模型对比"     → detailed model comparison report`);
  console.log(`  "关注安全性"       → security-focused report`);
  console.log(`  "聚焦实际应用案例" → real-world case studies report`);
  console.log(`  other / skip      → default general report`);
  console.log(`\nSpeed: add ?speed=fast or ?speed=slow to /api/research`);
});
