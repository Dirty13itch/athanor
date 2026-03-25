# n8n Signal Pipeline — Signal Messenger Integration for Athanor

**Date:** 2026-03-24
**Status:** Research complete, ready for implementation
**Author:** Claude (Research Agent)

---

## 1. Context

Athanor currently uses ntfy (VAULT:8880) for push notifications and has an OpenFang Telegram bot. The goal is to replace Telegram with Signal as the primary messaging interface, enabling:

- Two-way chat with Athanor agents from Signal
- Push notifications (alerts, briefings, security advisories)
- Group chat for "house" context (home automation, media, etc.)
- Mobile-first interaction when away from the Command Center dashboard

n8n is already running on VAULT:5678 with the RSS/intelligence signal pipeline. This research evaluates how to add Signal as an input/output channel through n8n.

---

## 2. Options Evaluated

### Option A: signal-cli-rest-api + n8n Community Node (RECOMMENDED)

**Architecture:** `bbernhard/signal-cli-rest-api` Docker container exposes a REST API wrapping `signal-cli`. n8n uses a community node to trigger on incoming messages and send responses.

**Components:**
- `bbernhard/signal-cli-rest-api:latest` (v0.98, March 2026) — Docker image, ~200MB
- Community node: `n8n-nodes-signal-cli-rest-api` (v0.8.1) by ZBlaZe/docdimy — WebSocket trigger + send actions
- Alternative community node: `n8n-nodes-signal-cli` (v0.2.0) by FGRibreau — connects to signal-cli daemon directly (not REST API)
- Alternative community node: `n8n-signal-trigger` by cgiesche — WebSocket trigger only

**Pros:**
- Simplest architecture: 1 additional container + 1 community node
- signal-cli-rest-api is mature (98 releases, actively maintained)
- REST API is well-documented with Swagger UI
- Supports sending to individuals and groups
- WebSocket endpoint for real-time message reception in JSON-RPC mode
- No additional infrastructure (no Matrix server, no database)
- Links as secondary device to existing Signal account (no new phone number needed)
- ~200MB RAM (JSON-RPC mode)

**Cons:**
- signal-cli is unofficial (reverse-engineered Signal protocol)
- Community node is third-party (not official n8n)
- Signal may ban accounts doing high-volume automated messaging
- JVM-based in JSON-RPC mode (higher memory than native mode)

### Option B: signal-cli Native Daemon + n8n HTTP Nodes

**Architecture:** Run `signal-cli` in daemon mode with `--http` flag (native JSON-RPC endpoint). n8n polls or connects via WebSocket using built-in HTTP/webhook nodes — no community node needed.

**Components:**
- `registry.gitlab.io/packaging/signal-cli/signal-cli-native:latest` — official signal-cli Docker image
- n8n built-in HTTP Request nodes + Webhook nodes

**Pros:**
- No community node dependency — uses only built-in n8n nodes
- signal-cli-native uses GraalVM (lower memory than JVM)
- Direct control over all API calls

**Cons:**
- Must implement WebSocket polling manually in n8n (Code node)
- No REST API convenience layer — must use JSON-RPC protocol directly
- Fewer examples and community support
- Registration is more complex without REST API helpers
- Must handle message formatting, group IDs, attachments manually

### Option C: Matrix (Conduit/Synapse) + mautrix-signal Bridge

**Architecture:** Run a Matrix homeserver + mautrix-signal bridge. n8n integrates via Matrix REST API. Signal messages are bridged bidirectionally to Matrix rooms.

**Components:**
- `matrixconduit/matrix-conduit` or `matrixdotorg/synapse` — Matrix homeserver
- `dock.mau.dev/mautrix/signal` — Signal bridge (Go, latest release Dec 2025)
- PostgreSQL for Synapse (Conduit uses embedded RocksDB)
- n8n connects to Matrix API via HTTP Request nodes

**Pros:**
- Bridges multiple protocols (Signal, Telegram, Discord, IRC) through one interface
- Matrix provides a native chat protocol with rooms, threading, reactions
- mautrix-signal is actively maintained (by Matrix.org ecosystem)
- Future-proof: adding Telegram/Discord/WhatsApp is just another bridge
- Proper message history and search via Matrix
- E2E encryption support between bridge and clients

**Cons:**
- Massive infrastructure overhead: Matrix server + PostgreSQL + bridge + bridge database
- Estimated 500MB-1GB+ additional RAM (Synapse is notoriously heavy; Conduit is lighter at ~100MB)
- Significant operational complexity for a single-user homelab
- Debugging bridge issues is painful (double-hop: Signal -> bridge -> Matrix -> n8n)
- Latency: messages traverse two protocols
- Violates Athanor's "one-person scale" principle — "Can Shaun understand, operate, debug, and fix this alone?"

### Option D: ntfy + Signal (notification-only, no two-way)

**Architecture:** Keep ntfy for one-way push notifications. Use ntfy's UnifiedPush or direct HTTP POST. Add Signal notification via signal-cli-rest-api send-only (no receive).

**Pros:**
- Simplest possible — ntfy already works
- No message reception complexity
- Zero risk of Signal account ban

**Cons:**
- No two-way communication
- Cannot chat with agents from Signal
- Doesn't achieve the stated goal

---

## 3. Deep Dive: Option A (Recommended)

### 3.1 signal-cli-rest-api Operating Modes

| Mode | Backend | Speed | RAM | Receive Method | Notes |
|------|---------|-------|-----|----------------|-------|
| `normal` | signal-cli JAR per request | Slow | Low (per-invocation) | GET /v1/receive | Cold-start on each call |
| `native` | GraalVM native binary | Fast | Low (~50MB) | GET /v1/receive | Experimental, no ARM |
| `json-rpc` | JVM daemon (supervisord) | Fastest | High (~200MB) | WebSocket | **Recommended for n8n** |
| `json-rpc-native` | GraalVM daemon | Fast | Medium (~100MB) | WebSocket | Newest, best balance |

**Recommendation: `json-rpc` mode.** The n8n community node `n8n-nodes-signal-cli-rest-api` uses WebSocket to listen for incoming messages, which requires `json-rpc` or `json-rpc-native` mode. JSON-RPC mode is the most tested and documented.

### 3.2 Registration / Linking

There are two ways to authenticate signal-cli-rest-api:

**Method 1: Link as secondary device (RECOMMENDED)**
1. Start the container
2. Open `http://VAULT:8082/v1/qrcodelink?device_name=athanor-signal`
3. Scan QR code from Signal mobile app (Settings > Linked Devices)
4. Done — uses Shaun's existing Signal number, no new registration needed

**Method 2: Register new number**
1. Requires a phone number that can receive SMS or voice calls
2. VoIP/SIP numbers work (use `--voice` for verification)
3. Must solve CAPTCHA at `https://signalcaptchas.org/registration/generate.html`
4. Token expires quickly — must register within 30 seconds of solving CAPTCHA
5. Verify: `POST /v1/register/<number>/verify/<code>`

**Recommendation: Method 1 (link as secondary device).** Simpler, no new number needed, inherits existing contacts and groups. The container acts as another "device" on Shaun's Signal account.

### 3.3 Docker Compose

```yaml
# signal-cli-rest-api — Signal messaging gateway for n8n
# Deploy on VAULT alongside n8n
services:
  signal-api:
    image: bbernhard/signal-cli-rest-api:latest
    container_name: signal-api
    restart: unless-stopped
    environment:
      - MODE=json-rpc
      - PORT=8080
      - TZ=America/Chicago
      # Prevent auto-downloading large attachments
      - JSON_RPC_IGNORE_STORIES=true
      - JSON_RPC_IGNORE_AVATARS=true
      - JSON_RPC_IGNORE_STICKERS=true
    ports:
      - "8082:8080"
    volumes:
      - signal-cli-data:/home/.local/share/signal-cli
    networks:
      - signals-net
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  signal-cli-data:

networks:
  signals-net:
    external: true
```

**Port assignment:** 8082 on VAULT. Does not conflict with existing services (8070=Miniflux, 8080=SABnzbd, 8088=Ulrich Energy).

### 3.4 n8n Community Node Installation

The n8n container needs `N8N_COMMUNITY_PACKAGES_ENABLED=true` in its environment. Then install `n8n-nodes-signal-cli-rest-api` from the n8n UI (Settings > Community Nodes > Install).

Updated n8n environment variables:
```yaml
env:
  N8N_COMMUNITY_PACKAGES_ENABLED: "true"
  # ... existing vars ...
```

### 3.5 n8n Credential Configuration

After installing the community node, create a new credential in n8n:
- **Type:** Signal CLI REST API
- **API URL:** `http://signal-api:8082` (or `http://192.168.1.203:8082` if not on same Docker network)
- **Phone Number:** Shaun's Signal number (the one linked in step 3.2)
- **Mode:** json-rpc

### 3.6 API Endpoints (signal-cli-rest-api)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/qrcodelink?device_name=X` | GET | Generate QR code for device linking |
| `/v2/send` | POST | Send message (text, attachments, groups) |
| `/v1/receive/<number>` | GET/WS | Receive messages (WebSocket in json-rpc mode) |
| `/v1/groups/<number>` | GET | List groups |
| `/v1/groups/<number>` | POST | Create group |
| `/v1/groups/<number>/<id>` | DELETE | Delete/leave group |
| `/v1/about` | GET | API version and mode info |
| `/v1/health` | GET | Health check |
| `/v1/attachments` | GET | List stored attachments |

### 3.7 Message Format

**Send to individual:**
```json
POST /v2/send
{
  "message": "Hello from Athanor",
  "number": "+1SENDER_NUMBER",
  "recipients": ["+1RECIPIENT_NUMBER"]
}
```

**Send to group:**
```json
POST /v2/send
{
  "message": "Hello from Athanor",
  "number": "+1SENDER_NUMBER",
  "recipients": ["group.BASE64_GROUP_ID"]
}
```

**Received message (WebSocket payload):**
```json
{
  "envelope": {
    "source": "+1SENDER_NUMBER",
    "sourceDevice": 1,
    "timestamp": 1711234567890,
    "dataMessage": {
      "timestamp": 1711234567890,
      "message": "Hey Athanor, what's the GPU status?",
      "groupInfo": {
        "groupId": "BASE64_GROUP_ID",
        "type": "DELIVER"
      }
    }
  }
}
```

---

## 4. n8n Workflow Design

### Workflow 1: Signal Chat Agent (bidirectional)

```
Signal Message → Parse → Route to Agent → Wait for Response → Send Reply via Signal
```

**Nodes:**

1. **Signal Trigger** (community node) — WebSocket listener for incoming Signal messages
2. **Parse Message** (Code node) — Extract sender, text, group info, thread context
3. **Sender Whitelist** (If node) — Only process messages from Shaun's number (security)
4. **Route to Agent** (HTTP Request) — POST to `http://192.168.1.244:9000/v1/chat/completions`
5. **Format Response** (Code node) — Truncate if >4000 chars, add formatting
6. **Send Reply** (Signal Send / HTTP Request) — POST to `http://signal-api:8082/v2/send`

**Node 2 — Parse Message (Code node):**
```javascript
const envelope = $input.item.json.envelope || $input.item.json;
const dataMsg = envelope.dataMessage || {};
const sender = envelope.source || '';
const messageText = dataMsg.message || '';
const groupId = dataMsg.groupInfo?.groupId || null;
const timestamp = dataMsg.timestamp || Date.now();

// Determine target agent from prefix commands
let agent = 'general-assistant';
let cleanMessage = messageText;

const prefixMap = {
  '/home': 'home-agent',
  '/media': 'media-agent',
  '/research': 'research-agent',
  '/creative': 'creative-agent',
  '/knowledge': 'knowledge-agent',
  '/code': 'coding-agent',
  '/stash': 'stash-agent',
  '/data': 'data-curator',
};

for (const [prefix, agentName] of Object.entries(prefixMap)) {
  if (messageText.toLowerCase().startsWith(prefix)) {
    agent = agentName;
    cleanMessage = messageText.slice(prefix.length).trim();
    break;
  }
}

return {
  json: {
    sender,
    message: cleanMessage,
    agent,
    groupId,
    timestamp,
    isGroup: !!groupId,
    raw: messageText,
  }
};
```

**Node 4 — Route to Agent (HTTP Request):**
```
POST http://192.168.1.244:9000/v1/chat/completions

{
  "model": "{{ $json.agent }}",
  "messages": [
    {
      "role": "system",
      "content": "You are responding via Signal messenger. Keep responses concise (under 2000 characters). Use plain text, no markdown. The user is Shaun, Athanor's operator."
    },
    {
      "role": "user",
      "content": "{{ $json.message }}"
    }
  ],
  "max_tokens": 1024,
  "temperature": 0.7
}
```

**Node 6 — Send Reply (HTTP Request):**
```
POST http://192.168.1.203:8082/v2/send

{
  "message": "{{ $json.choices[0].message.content }}",
  "number": "+1ATHANOR_NUMBER",
  "recipients": ["{{ $json.isGroup ? 'group.' + $json.groupId : $json.sender }}"]
}
```

### Workflow 2: Signal Notification Forwarder

Replaces ntfy for critical alerts. Triggered by other n8n workflows or external webhooks.

```
Webhook/Schedule → Format Alert → Send via Signal
```

**Trigger:** n8n Webhook at `/webhook/signal-notify`
**Input format:**
```json
{
  "message": "CRITICAL: GPU 2 temperature exceeded 90C",
  "priority": "critical",
  "target": "shaun"  // or "house-group"
}
```

### Workflow 3: Signal Morning Briefing

Extends existing signal-digest workflow (12.2) to deliver via Signal.

```
Schedule 6:30 AM → Query signals/activity → Summarize via LLM → Send to Signal
```

### Workflow 4: Signal → Home Assistant

Route home commands directly.

```
Signal "/home ..." → Parse → POST to HA API → Confirm via Signal
```

---

## 5. Async Response Pattern (Agent Latency)

Agent responses can take 5-30+ seconds (tool calls, multi-step reasoning). Two approaches:

### Approach A: Synchronous Wait (Simple)
- n8n waits for the HTTP response from the agent server
- Set HTTP Request timeout to 120s
- Signal shows "delivered" then response appears later
- User might send another message while waiting

**Verdict:** Good enough for v1. Agent server responds in 2-15s for most queries.

### Approach B: Async with Typing Indicator (Advanced, future)
1. Signal Trigger receives message
2. n8n sends "thinking..." typing indicator via Signal API
3. n8n POSTs to agent server (async task)
4. n8n polls/waits for task completion
5. Sends actual response

**Verdict:** Nice-to-have for v2. Requires agent server task queue endpoint.

---

## 6. Security Considerations

### 6.1 Signal Account Security
- **Linked device model:** signal-cli-rest-api links as a secondary device. If the container is compromised, an attacker can read/send messages as Shaun.
- **Mitigation:** Restrict port 8082 to LAN only (firewall). Do not expose to internet.
- **Key backup:** The volume `signal-cli-data` contains Signal identity keys. Include in VAULT backup strategy.

### 6.2 Sender Whitelist
- The n8n workflow MUST filter by sender phone number before routing to agents
- Only Shaun's number should trigger agent interactions
- Group messages: filter by group ID (only process from "Athanor House" group)

### 6.3 Rate Limits
- Signal enforces undocumented rate limits. Accounts sending many messages to new contacts risk "Rate limit exceeded: 413" errors.
- For Athanor's use case (1 user, handful of messages/day), this is not a concern.
- Avoid sending more than ~10 messages per minute to be safe.
- The Signal API does not have published rate limit numbers, so we rely on community experience.

### 6.4 Content Routing
- NSFW/sovereign content MUST NOT traverse Signal (cloud protocol, not E2E for bots)
- Route Stash agent and uncensored queries through dashboard only, never Signal
- Add content filter in the n8n Parse Message node

### 6.5 Signal Registration Resilience
- Linked device sessions can expire if the primary device is inactive for 30+ days
- If signal-cli-rest-api container is rebuilt, the linked device must be re-linked
- Signal protocol updates may temporarily break signal-cli

---

## 7. Resource Budget

| Component | RAM | Disk | CPU |
|-----------|-----|------|-----|
| signal-cli-rest-api (json-rpc) | ~200MB | ~50MB (+ attachments) | <0.5 core |
| n8n community node | ~0 (part of n8n) | ~5MB | ~0 |
| **Total additional** | **~200MB** | **~55MB** | **<0.5 core** |

VAULT has 128GB RAM. Current utilization is moderate. This is negligible.

---

## 8. Implementation Order

1. **Update n8n Ansible role** — Add `N8N_COMMUNITY_PACKAGES_ENABLED=true` environment variable
2. **Create Ansible role `vault-signal-api`** — Deploy signal-cli-rest-api container on VAULT:8082
3. **Deploy and link** — Start container, scan QR code from Shaun's phone
4. **Install n8n community node** — `n8n-nodes-signal-cli-rest-api` via n8n UI
5. **Create n8n credential** — Signal CLI REST API with VAULT:8082 and phone number
6. **Import Workflow 1** — Signal Chat Agent (bidirectional)
7. **Import Workflow 2** — Signal Notification Forwarder
8. **Test end-to-end** — Send message from Signal, verify agent response
9. **Import Workflows 3-4** — Morning Briefing + Home Assistant
10. **Update SERVICES.md** — Add signal-api to VAULT services
11. **Backup config** — Add `signal-cli-data` volume to VAULT backup

---

## 9. Ansible Role: `vault-signal-api`

### `defaults/main.yml`
```yaml
---
signal_api_image: "bbernhard/signal-cli-rest-api:latest"
signal_api_port: 8082
signal_api_data_path: "/mnt/appdatacache/signal-api"
signal_api_mode: "json-rpc"
```

### `tasks/main.yml`
```yaml
---
- name: Create signal-api data directory
  ansible.builtin.file:
    path: "{{ signal_api_data_path }}"
    state: directory
    mode: "0755"
    owner: "1000"
    group: "1000"

- name: Run signal-api container
  community.docker.docker_container:
    name: signal-api
    image: "{{ signal_api_image }}"
    state: started
    restart_policy: unless-stopped
    ports:
      - "{{ signal_api_port }}:8080"
    volumes:
      - "{{ signal_api_data_path }}:/home/.local/share/signal-cli"
    env:
      MODE: "{{ signal_api_mode }}"
      TZ: "America/Chicago"
      JSON_RPC_IGNORE_STORIES: "true"
      JSON_RPC_IGNORE_AVATARS: "true"
      JSON_RPC_IGNORE_STICKERS: "true"
    networks:
      - name: signals-net
    log_driver: json-file
    log_options:
      max-size: "10m"
      max-file: "3"
  when: not ansible_check_mode

- name: Wait for signal-api to be ready
  ansible.builtin.uri:
    url: "http://localhost:{{ signal_api_port }}/v1/about"
    status_code: 200
  register: signal_api_ready
  retries: 10
  delay: 5
  when: not ansible_check_mode
```

---

## 10. n8n Workflow JSON: Signal Chat Agent

```json
{
  "name": "Signal Chat Agent",
  "nodes": [
    {
      "parameters": {},
      "id": "signal-trigger-1",
      "name": "Signal Trigger",
      "type": "n8n-nodes-signal-cli-rest-api.signalTrigger",
      "typeVersion": 1,
      "position": [240, 300]
    },
    {
      "parameters": {
        "jsCode": "// Parse incoming Signal message\nconst data = $input.item.json;\nconst envelope = data.envelope || data;\nconst dataMsg = envelope.dataMessage || {};\nconst sender = envelope.source || envelope.sourceNumber || '';\nconst messageText = dataMsg.message || '';\nconst groupId = dataMsg.groupInfo?.groupId || null;\n\n// Route by prefix command\nlet agent = 'general-assistant';\nlet cleanMessage = messageText;\nconst prefixes = {\n  '/home': 'home-agent',\n  '/media': 'media-agent',\n  '/research': 'research-agent',\n  '/creative': 'creative-agent',\n  '/knowledge': 'knowledge-agent',\n  '/code': 'coding-agent',\n  '/stash': 'stash-agent',\n  '/data': 'data-curator',\n};\nfor (const [p, a] of Object.entries(prefixes)) {\n  if (messageText.toLowerCase().startsWith(p)) {\n    agent = a;\n    cleanMessage = messageText.slice(p.length).trim();\n    break;\n  }\n}\n\nreturn {\n  json: { sender, message: cleanMessage, agent, groupId, isGroup: !!groupId, raw: messageText }\n};"
      },
      "id": "parse-message-1",
      "name": "Parse Message",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [460, 300]
    },
    {
      "parameters": {
        "conditions": {
          "options": { "caseSensitive": false },
          "combinator": "and",
          "conditions": [
            {
              "leftValue": "={{ $json.sender }}",
              "rightValue": "SHAUN_PHONE_NUMBER",
              "operator": { "type": "string", "operation": "equals" }
            }
          ]
        }
      },
      "id": "whitelist-1",
      "name": "Sender Whitelist",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [680, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://192.168.1.244:9000/v1/chat/completions",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ model: $json.agent, messages: [{ role: 'system', content: 'You are responding via Signal messenger. Keep responses concise (under 2000 chars). Use plain text, no markdown headers or code fences. The user is Shaun, Athanor operator.' }, { role: 'user', content: $json.message }], max_tokens: 1024, temperature: 0.7 }) }}",
        "options": { "timeout": 120000 }
      },
      "id": "agent-request-1",
      "name": "Route to Agent",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [900, 200]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "=http://192.168.1.203:8082/v2/send",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ message: $('Route to Agent').item.json.choices[0].message.content.substring(0, 4000), number: 'ATHANOR_SIGNAL_NUMBER', recipients: [$('Parse Message').item.json.isGroup ? 'group.' + $('Parse Message').item.json.groupId : $('Parse Message').item.json.sender] }) }}"
      },
      "id": "send-reply-1",
      "name": "Send Reply",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [1120, 200]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://192.168.1.203:8082/v2/send",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ message: 'Sorry, I can only respond to messages from authorized users.', number: 'ATHANOR_SIGNAL_NUMBER', recipients: [$json.sender] }) }}"
      },
      "id": "reject-1",
      "name": "Reject Unauthorized",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [900, 450]
    }
  ],
  "connections": {
    "Signal Trigger": { "main": [[{ "node": "Parse Message", "type": "main", "index": 0 }]] },
    "Parse Message": { "main": [[{ "node": "Sender Whitelist", "type": "main", "index": 0 }]] },
    "Sender Whitelist": {
      "main": [
        [{ "node": "Route to Agent", "type": "main", "index": 0 }],
        [{ "node": "Reject Unauthorized", "type": "main", "index": 0 }]
      ]
    },
    "Route to Agent": { "main": [[{ "node": "Send Reply", "type": "main", "index": 0 }]] }
  }
}
```

**Note:** Replace `SHAUN_PHONE_NUMBER` and `ATHANOR_SIGNAL_NUMBER` with actual values before importing.

---

## 11. Comparison Summary

| Criterion | A: signal-cli-rest-api | B: signal-cli native | C: Matrix bridge | D: ntfy only |
|-----------|----------------------|---------------------|-----------------|--------------|
| Two-way chat | Yes | Yes | Yes | No |
| Setup complexity | Low (1 container + node) | Medium (manual WS) | High (3+ containers) | None |
| Additional RAM | ~200MB | ~100MB | ~500MB-1GB | 0 |
| Community support | Strong | Moderate | Strong | N/A |
| Maintenance burden | Low | Medium | High | None |
| Group support | Yes | Yes | Yes | N/A |
| Multi-protocol future | No | No | Yes (bridges) | No |
| One-person scale | Yes | Yes | No | Yes |
| Risk of breakage | Medium (unofficial) | Medium (unofficial) | Low (Matrix is stable) | None |

---

## 12. Open Questions / Blockers

1. **Phone number for linking:** Shaun needs to scan a QR code from his Signal app to link the container. This is a one-time manual step.

2. **Stash/NSFW routing:** The n8n workflow must block `/stash` prefix commands via Signal. These should only work through the dashboard (local, no cloud protocol transit).

3. **Community node version pinning:** `n8n-nodes-signal-cli-rest-api` is at v0.8.1. Should be monitored for breaking changes when n8n updates.

4. **Signal protocol updates:** Signal occasionally makes protocol changes that break unofficial clients. signal-cli typically catches up within days, but there may be brief outages.

5. **Conversation threading:** The current design is stateless (each message is independent). For multi-turn conversations, we'd need to pass `thread_id` to the agent server based on sender + time window. This is a v2 enhancement.

6. **Image/attachment handling:** signal-cli-rest-api supports sending base64 attachments. Future workflow could send ComfyUI-generated images or charts via Signal.

---

## 13. Recommendation

**Go with Option A: signal-cli-rest-api + n8n community node.**

Rationale:
- Lowest complexity that achieves full bidirectional messaging
- Fits Athanor's "one-person scale" principle
- Minimal resource overhead (~200MB RAM)
- Proven path: n8n workflow template exists, community node is actively maintained
- Linking as secondary device means no new phone number needed
- n8n already running on VAULT — this is just one more container + one more workflow

The Matrix bridge (Option C) would be the right choice if Athanor needed to integrate 3+ messaging protocols simultaneously. For Signal-only, it's overkill.

---

## Sources

- [bbernhard/signal-cli-rest-api — GitHub](https://github.com/bbernhard/signal-cli-rest-api)
- [signal-cli-rest-api — Docker Hub](https://hub.docker.com/r/bbernhard/signal-cli-rest-api)
- [signal-cli-rest-api — API Documentation](https://bbernhard.github.io/signal-cli-rest-api/)
- [signal-cli-rest-api — Examples](https://github.com/bbernhard/signal-cli-rest-api/blob/master/doc/EXAMPLES.md)
- [n8n-nodes-signal-cli-rest-api — npm](https://www.npmjs.com/package/n8n-nodes-signal-cli-rest-api)
- [ZBlaZe/n8n-nodes-signal (community node) — GitHub](https://github.com/ZBlaZe/n8n-nodes-signal)
- [docdimy/signal-community-node — GitHub](https://github.com/docdimy/signal-community-node)
- [FGRibreau/n8n-nodes-signal-cli — GitHub](https://github.com/FGRibreau/n8n-nodes-signal-cli)
- [cgiesche/n8n-signal-trigger — GitHub](https://github.com/cgiesche/n8n-signal-trigger)
- [n8n Signal+AI Workflow Template](https://n8n.io/workflows/10661-create-a-secure-personal-ai-assistant-with-openai-and-signal-messenger/)
- [signal-cli Registration with Captcha — Wiki](https://github.com/AsamK/signal-cli/wiki/Registration-with-captcha)
- [signal-cli Rate Limit Issues — GitHub](https://github.com/AsamK/signal-cli/issues/1603)
- [mautrix-signal (Matrix bridge) — GitHub](https://github.com/mautrix/signal)
- [n8n Community Nodes Installation — Docs](https://docs.n8n.io/integrations/community-nodes/installation/)
- [Signal CLI REST Webhook Discussion](https://github.com/bbernhard/signal-cli-rest-api/issues/74)
- [n8n Nodes Environment Variables — Docs](https://docs.n8n.io/hosting/configuration/environment-variables/nodes/)

Last updated: 2026-03-24
