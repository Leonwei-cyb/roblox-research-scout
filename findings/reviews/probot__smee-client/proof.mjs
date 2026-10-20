// Isolated proof for probot/smee-client @ 6c40610: everything on 127.0.0.1, no smee.io, no GitHub.
// 1) relay.js: emulates smee.io (POST /ch -> parse JSON body -> SSE event {...headers, body, query, timestamp}),
//    which is what smee.io's server does (it parses the body, so the raw bytes are gone before the client sees them).
// 2) target: receives the forwarded POST, records arrival time, verifies X-Hub-Signature-256 over the RAW bytes it got.
// 3) SmeeClient from the pinned, locally built index.js connects relay -> target.
import http from "node:http";
import crypto from "node:crypto";
import SmeeClient from "../smee-client/index.js";

const SECRET = "proof-only-secret";
const sign = (buf) => "sha256=" + crypto.createHmac("sha256", SECRET).update(buf).digest("hex");
const clients = new Set();
const sent = new Map();
const results = [];

const relay = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/ch") {
    res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "keep-alive" });
    res.write("event: ready\ndata: {}\n\n");
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return;
  }
  let chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    const msg = JSON.stringify({ ...req.headers, body, query: {}, timestamp: Date.now() });
    for (const c of clients) c.write(`data: ${msg}\n\n`);
    res.writeHead(200).end("ok");
  });
});

const target = http.createServer((req, res) => {
  let chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    const raw = Buffer.concat(chunks);
    const id = req.headers["x-github-delivery"];
    const t0 = sent.get(id);
    results.push({
      id, kind: req.headers["x-proof-kind"], ms: Number(process.hrtime.bigint() - t0.at) / 1e6,
      signatureValid: sign(raw) === req.headers["x-hub-signature-256"],
      bytesEqual: raw.equals(t0.raw), event: req.headers["x-github-event"],
    });
    res.writeHead(200).end("ok");
  });
});

const listen = (srv) => new Promise((r) => srv.listen(0, "127.0.0.1", () => r(srv.address().port)));
const relayPort = await listen(relay);
const targetPort = await listen(target);
const quiet = { info() {}, error(...a) { console.error("client error", ...a); } };
const client = new SmeeClient({ source: `http://127.0.0.1:${relayPort}/ch`, target: `http://127.0.0.1:${targetPort}/hook`, logger: quiet });
await client.start();

// Payload shapes: compact ASCII (how GitHub serialises most payloads), plus byte forms that
// JSON.parse -> JSON.stringify does not preserve.
const kinds = {
  "compact-ascii": (i) => Buffer.from(JSON.stringify({ action: "created", comment: { id: i, body: "ACK " + i }, repository: { full_name: "Leonwei-cyb/Roblox-Studio-Hub" } })),
  "pretty-printed": (i) => Buffer.from(JSON.stringify({ action: "created", n: i }, null, 2)),
  "unicode-escaped": (i) => Buffer.from(`{"action":"created","n":${i},"body":"caf\\u00e9 \\u003cb\\u003e"}`),
  "float-1.0": (i) => Buffer.from(`{"action":"created","n":${i},"score":1.0}`),
};
const post = (raw, kind, id) => new Promise((resolve, reject) => {
  const req = http.request({ host: "127.0.0.1", port: relayPort, path: "/ch", method: "POST", headers: {
    "content-type": "application/json", "x-github-event": "issue_comment", "x-github-delivery": id,
    "x-hub-signature-256": sign(raw), "x-proof-kind": kind } }, (res) => { res.resume(); res.on("end", resolve); });
  req.on("error", reject);
  sent.set(id, { at: process.hrtime.bigint(), raw });
  req.end(raw);
});
const N = 50;
for (const [kind, make] of Object.entries(kinds)) {
  for (let i = 0; i < (kind === "compact-ascii" ? N : 5); i++) {
    await post(make(i), kind, `${kind}-${i}`);
  }
}
// Network blip: drop the SSE stream, publish while disconnected, then publish again.
await new Promise((r) => setTimeout(r, 300));
for (const c of clients) c.destroy();
clients.clear();
await post(kinds["compact-ascii"](900), "blip", "blip-during-drop");
const reconnectStart = Date.now();
while (clients.size === 0 && Date.now() - reconnectStart < 10000) await new Promise((r) => setTimeout(r, 10));
const reconnectMs = Date.now() - reconnectStart;
await new Promise((r) => setTimeout(r, 50));
await post(kinds["compact-ascii"](901), "blip", "blip-after-reconnect");
const deadline = Date.now() + 5000;
while (results.length < N + 16 && Date.now() < deadline) await new Promise((r) => setTimeout(r, 20));
await client.stop();
relay.close(); target.close();
for (const c of clients) c.end();

const summary = {};
for (const kind of Object.keys(kinds)) {
  const rows = results.filter((r) => r.kind === kind);
  const ms = rows.map((r) => r.ms).sort((a, b) => a - b);
  summary[kind] = {
    sent: kind === "compact-ascii" ? N : 5, delivered: rows.length,
    signatureValid: rows.filter((r) => r.signatureValid).length,
    bytesIdentical: rows.filter((r) => r.bytesEqual).length,
    p50_ms: ms.length ? +ms[Math.floor(ms.length * 0.5)].toFixed(2) : null,
    p95_ms: ms.length ? +ms[Math.min(ms.length - 1, Math.floor(ms.length * 0.95))].toFixed(2) : null,
  };
}
const blip = results.filter((r) => r.kind === "blip").map((r) => r.id);
console.log(JSON.stringify({ node: process.version, summary,
  reconnect: { reconnect_ms: reconnectMs, delivered: blip, lost: ["blip-during-drop", "blip-after-reconnect"].filter((x) => !blip.includes(x)) } }, null, 2));
process.exit(0);
