# Empire of Broken Queens

AI-driven interactive cinematic adult game. All dialogue generated at runtime via LLM. All images generated at runtime via ComfyUI.

## Architecture

See `docs/projects/eoq/ARCHITECTURE.md` for the full design.

**Key insight:** EoBQ is a real-time AI dialogue system with a visual novel presentation layer. It is NOT a traditional VN with pre-authored branching content.

```
Browser
  |
  +---> Next.js App (Node 2, port 3002)
          |
          +-- React UI (VN presentation components)
          |     - SceneBackground (full-screen with crossfade)
          |     - CharacterPortrait (positioned sprite)
          |     - DialogueBox (streaming typewriter text)
          |     - ChoicePanel (player decisions)
          |
          +-- Zustand stores (client-side state)
          |     - Game session, characters, world, UI
          |
          +-- Next.js API routes (server-side proxy)
                |
                +---> LiteLLM (VAULT:4000) -- dialogue generation (streaming SSE)
                +---> ComfyUI (Node 2:8188) -- image generation
                +---> Qdrant (Node 1:6333) -- character memory retrieval
```

## Tech Stack

| Component | Technology | ADR |
|-----------|-----------|-----|
| Runtime | Next.js 16, React 19 | ADR-014 |
| Styling | Tailwind CSS + Framer Motion | |
| State | Zustand (client), SQLite (persistence) | |
| LLM | LiteLLM proxy -> sovereign local text aliases (`uncensored`, `reasoning`, `creative`) currently consolidated on Foundry | ADR-005, ADR-012 |
| Images | ComfyUI + Flux dev FP8 | ADR-006 |
| Memory | Qdrant vector search | |

## Project Structure

```
projects/eoq/
  comfyui/          -- EOQ-pinned workflow copies and EOQ-specific workflow variants
  src/
    app/
      api/chat/     -- Dialogue generation (LiteLLM proxy + streaming)
      api/generate/ -- Image generation (ComfyUI proxy)
      components/   -- VN presentation components
      page.tsx      -- Main game page
      layout.tsx    -- Root layout
      globals.css   -- Theme and base styles
    stores/         -- Zustand state management
    lib/            -- Configuration, utilities
    types/          -- TypeScript type definitions
  package.json
  tsconfig.json
  next.config.ts
```

## Development

```bash
cd projects/eoq
npm install
npm run dev    # http://localhost:3002
```

Mock mode is enabled by default in development — UI iteration without GPU cost.

## Status

**Active scaffold.** Core types, stores, VN components, and API routes are in place. Runtime dialogue and narration stay on the sovereign local `uncensored` lane; reusable promoted workflow templates belong in `projects/comfyui-workflows` and EOQ keeps only pinned copies or EOQ-specific variants.

Remaining build needs:

1. Mock data for a playable test scene
2. npm install + build verification
3. Game loop (connect choices -> API -> state updates -> re-render)
4. ComfyUI workflow loading (use existing JSONs from comfyui/)
5. Save/load game state
6. Character definitions for the first scenario
