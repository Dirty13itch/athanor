# Athanor Dashboard

Next.js 15 dashboard for monitoring and interacting with the Athanor homelab.

## Stack

- **Next.js 16** (App Router, Turbopack)
- **TypeScript**
- **Tailwind CSS v4** + **shadcn/ui** (zinc dark theme)
- Server components for data fetching, client components for interactivity

## Pages

| Route | Description |
|-------|-------------|
| `/` | Overview — node cards, service health summary, quick links |
| `/gpu` | GPU metrics from Prometheus DCGM exporter (15s revalidate) |
| `/chat` | Streaming chat interface connected to vLLM on Node 1 |
| `/services` | Health checks for all monitored services grouped by node |

## API Routes

| Route | Description |
|-------|-------------|
| `POST /api/chat` | Proxies streaming chat completions to vLLM |

## Configuration

All service URLs are in `src/lib/config.ts`. Override with environment variables:

- `NEXT_PUBLIC_PROMETHEUS_URL` — default `http://192.168.1.203:9090`
- `NEXT_PUBLIC_VLLM_URL` — default `http://192.168.1.244:8000`

## Running

```bash
cd projects/dashboard
npm run dev    # http://localhost:3000
npm run build  # production build
npm start      # serve production build
```

## Architecture

- `src/lib/config.ts` — centralized service URLs and node definitions
- `src/lib/api.ts` — Prometheus query helpers, vLLM chat API, service health checks
- `src/components/sidebar-nav.tsx` — sidebar navigation (client component)
- `src/app/api/chat/route.ts` — SSE proxy to vLLM for streaming
