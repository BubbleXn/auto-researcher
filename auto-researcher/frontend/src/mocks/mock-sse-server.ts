import { createServer } from "node:http";
import { createMockEventSequence } from "./mock-data";

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

const server = createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS_HEADERS);
    res.end();
    return;
  }

  if (req.method === "POST" && req.url?.startsWith("/api/research/input")) {
    res.writeHead(200, { ...CORS_HEADERS, "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  if (req.method === "POST" && req.url?.startsWith("/api/research")) {
    res.writeHead(200, SSE_HEADERS);

    const speed = new URL(
      req.url,
      `http://localhost:${PORT}`
    ).searchParams.get("speed");
    const multiplier = speed === "fast" ? 0.3 : speed === "slow" ? 2 : 1;

    const events = createMockEventSequence();
    let aborted = false;

    req.on("close", () => {
      aborted = true;
    });

    for (const { event, delay } of events) {
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
  console.log(`  POST /api/research      → SSE event stream`);
  console.log(`  POST /api/research/input → human input endpoint`);
  console.log(`  GET  /health            → health check`);
  console.log(`\nSpeed: add ?speed=fast or ?speed=slow to /api/research`);
});
