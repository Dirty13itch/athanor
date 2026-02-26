/**
 * ws-pty-bridge — WebSocket-to-PTY server for Athanor terminal page.
 *
 * Protocol:
 *   Client → Server: raw text (keystrokes) or JSON {type:"resize", cols, rows}
 *   Server → Client: raw text (terminal output)
 *
 * Node routing via ?node= query param:
 *   node2 → local bash
 *   node1 → ssh -tt node1
 *   dev   → ssh -tt 192.168.1.215
 */

const http = require("http");
const { WebSocketServer } = require("ws");
const pty = require("node-pty");
const url = require("url");

const PORT = parseInt(process.env.PORT || "3100", 10);
const MAX_CONNECTIONS = 5;
const HEARTBEAT_INTERVAL = 30000;

// Node routing: nodeId → command + args
const NODE_COMMANDS = {
  node2: { cmd: "/bin/bash", args: ["-l"] },
  node1: { cmd: "ssh", args: ["-tt", "-o", "StrictHostKeyChecking=no", "node1"] },
  dev: { cmd: "ssh", args: ["-tt", "-o", "StrictHostKeyChecking=no", "192.168.1.215"] },
};

let activeConnections = 0;

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", connections: activeConnections }));
    return;
  }
  res.writeHead(404);
  res.end("Not found");
});

const wss = new WebSocketServer({ server });

wss.on("connection", (ws, req) => {
  if (activeConnections >= MAX_CONNECTIONS) {
    ws.close(1013, "Too many connections");
    return;
  }

  const params = url.parse(req.url, true).query;
  const nodeId = params.node || "node2";
  const nodeConfig = NODE_COMMANDS[nodeId];

  if (!nodeConfig) {
    ws.send(`\r\n\x1b[31mUnknown node: ${nodeId}\x1b[0m\r\n`);
    ws.close(1008, "Unknown node");
    return;
  }

  activeConnections++;
  console.log(`[+] Connection to ${nodeId} (${activeConnections} active)`);

  const cols = parseInt(params.cols, 10) || 80;
  const rows = parseInt(params.rows, 10) || 24;

  let ptyProcess;
  try {
    ptyProcess = pty.spawn(nodeConfig.cmd, nodeConfig.args, {
      name: "xterm-256color",
      cols,
      rows,
      cwd: process.env.HOME || "/",
      env: {
        ...process.env,
        TERM: "xterm-256color",
        COLORTERM: "truecolor",
      },
    });
  } catch (err) {
    ws.send(`\r\n\x1b[31mFailed to spawn: ${err.message}\x1b[0m\r\n`);
    ws.close(1011, "PTY spawn failed");
    activeConnections--;
    return;
  }

  // PTY → WebSocket
  ptyProcess.onData((data) => {
    if (ws.readyState === ws.OPEN) {
      ws.send(data);
    }
  });

  ptyProcess.onExit(({ exitCode }) => {
    console.log(`[-] PTY exited for ${nodeId} (code ${exitCode})`);
    if (ws.readyState === ws.OPEN) {
      ws.send(`\r\n\x1b[90mProcess exited (code ${exitCode}).\x1b[0m\r\n`);
      ws.close(1000, "PTY exited");
    }
  });

  // WebSocket → PTY
  ws.on("message", (msg) => {
    const str = msg.toString();

    // Check for JSON resize message
    if (str.startsWith("{")) {
      try {
        const parsed = JSON.parse(str);
        if (parsed.type === "resize" && parsed.cols && parsed.rows) {
          ptyProcess.resize(
            Math.min(Math.max(parsed.cols, 10), 500),
            Math.min(Math.max(parsed.rows, 2), 200)
          );
          return;
        }
      } catch {
        // Not JSON — pass through as input
      }
    }

    ptyProcess.write(str);
  });

  ws.on("close", () => {
    activeConnections--;
    console.log(`[-] Disconnected from ${nodeId} (${activeConnections} active)`);
    ptyProcess.kill();
  });

  ws.on("error", (err) => {
    console.error(`[!] WebSocket error for ${nodeId}:`, err.message);
    ptyProcess.kill();
  });

  // Heartbeat
  ws.isAlive = true;
  ws.on("pong", () => { ws.isAlive = true; });
});

// Heartbeat sweep
const heartbeat = setInterval(() => {
  wss.clients.forEach((ws) => {
    if (!ws.isAlive) {
      ws.terminate();
      return;
    }
    ws.isAlive = false;
    ws.ping();
  });
}, HEARTBEAT_INTERVAL);

wss.on("close", () => clearInterval(heartbeat));

server.listen(PORT, "0.0.0.0", () => {
  console.log(`ws-pty-bridge listening on :${PORT}`);
});
