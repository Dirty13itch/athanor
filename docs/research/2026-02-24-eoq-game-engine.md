# EoQ Game Engine Selection

**Date:** 2026-02-24
**Status:** Complete -- recommendation ready
**Supports:** Future ADR (EoQ Game Engine)
**Depends on:** ADR-005 (Inference Engine), ADR-006 (Creative Pipeline), ADR-012 (LiteLLM Routing)

---

## The Question

What engine or framework should Empire of Broken Queens use for its interactive front-end? EoQ is not a conventional visual novel -- dialogue is generated at runtime by a local LLM (vLLM), images are generated at runtime by ComfyUI, and the narrative state is a complex data structure (personality vectors, relationship scores, memory logs, emotional states). The engine must handle async HTTP API calls as a first-class operation, not a bolt-on.

---

## Requirements

| # | Requirement | Weight |
|---|-------------|--------|
| 1 | Runtime HTTP API calls (vLLM + ComfyUI) with async/streaming support | Critical |
| 2 | Dynamic content display (non-pre-authored dialogue and images) | Critical |
| 3 | Rich state management (character vectors, relationships, world state) | Critical |
| 4 | No adult content restrictions in engine or distribution | Critical |
| 5 | One-person development with AI-assisted code generation | High |
| 6 | Web-deployable (browser-playable) | High |
| 7 | Cinematic VN presentation (portraits, backgrounds, dialogue, choices) | High |
| 8 | Save/load game state | Medium |
| 9 | Streaming text display (typewriter from LLM token stream) | Medium |
| 10 | Extensible for future features (video, audio, multiplayer) | Low |

---

## Options Evaluated

### Option 1: Ren'Py 8.5

**What it is:** The dominant visual novel engine. Python-based, open source (MIT), 8,000+ games built with it. Version 8.5.2 released January 2026.

**HTTP API support:**
- `renpy.fetch(url, method, json, result, timeout, headers)` -- built-in HTTP client since ~8.3
- Supports GET, POST, PUT with JSON payloads
- Works on desktop and web builds
- Web builds require CORS headers on the target server
- **Cannot stream responses** -- renpy.fetch() returns the complete response. No ReadableStream, no SSE, no WebSocket support
- Default 5-second timeout is too short for LLM generation (typical: 5-30s)
- Outside interactions: calls `renpy.pause()` while waiting (UI freezes visually)
- Inside interactions: blocks the display system entirely

**Dynamic content:**
- Designed for pre-authored content with variable substitution and conditional branching
- Dynamic text works via Python string formatting into dialogue
- Dynamic images work by changing which file is displayed
- But the entire paradigm assumes assets exist at build time
- No built-in concept of "wait for an image to be generated, then display it"

**State management:**
- Python variables in the `store` namespace
- Persistent data across sessions via `persistent` object
- Complex objects must be picklable (no arbitrary Python classes)
- Adequate for simple flags and counters, awkward for complex state (personality vectors, relationship matrices)
- No built-in database integration

**Adult content:**
- Zero engine restrictions. Ren'Py is the de facto engine for adult VNs on F95zone and itch.io
- Massive community of adult game developers
- Distribution: F95zone, itch.io, Patreon, self-hosted. Steam requires separate SFW/NSFW builds

**Solo dev complexity:**
- Very low barrier to entry for conventional VNs
- Ren'Py script language is simple and well-documented
- BUT: making it do unconventional things (async API calls, streaming, dynamic image loading) requires fighting the engine
- Python is AI-generatable, but Ren'Py's custom script syntax is niche

**Web deployment:**
- Emscripten/WASM-based web export exists
- **Networking limitation is critical:** `renpy.fetch()` works but cannot stream, cannot use WebSockets, and CORS must be configured on the API server
- No multithreading in web builds
- Files >50MB not cached (redownloaded each session)
- Image preloading doesn't work in web builds (causes frame drops)

**Verdict:** Ren'Py is optimized for a problem EoQ doesn't have (pre-authored branching narratives). Its HTTP support exists but cannot stream LLM responses, which destroys the user experience for AI-generated dialogue. The web build's networking limitations make it a poor fit for a system that lives on API calls.

**Sources:**
- [Ren'Py fetch documentation](https://www.renpy.org/doc/html/fetch.html)
- [Ren'Py web/HTML5 documentation](https://www.renpy.org/doc/html/web.html)
- [Ren'Py GitHub](https://github.com/renpy/renpy)
- [Ren'Py performance troubleshooting](https://mindfulchase.com/explore/troubleshooting-tips/game-development-tools/advanced-ren-py-troubleshooting-memory,-performance,-and-architecture.html)

---

### Option 2: Godot 4.4

**What it is:** Open-source general-purpose game engine. GDScript or C#, 2D/3D, exports to desktop/web/mobile.

**HTTP API support:**
- `HTTPRequest` node supports async HTTP requests natively
- Signals-based architecture: connect `request_completed` signal to handler
- Web export uses XMLHttpRequest under the hood -- CORS required
- Cannot progress HTTP requests more than once per frame in web builds
- No native streaming/SSE support -- would need custom implementation via JavaScript interop

**Dynamic content:**
- Full game engine -- can display anything at any time
- Dynamic texture loading from bytes/URLs is straightforward
- No paradigm assumptions about pre-authored vs generated content

**State management:**
- Full programming language (GDScript or C#) -- any data structure you want
- Resource system for serialization
- Autoload singletons for global state
- Adequate for complex state, but you build everything yourself

**Adult content:**
- Engine has no content restrictions
- Distribution platforms set their own rules (itch.io allows, Steam requires patches)
- Godot forums explicitly declined to add NSFW showcase category -- community is family-friendly, but engine is unrestricted
- Smaller adult game community than Ren'Py

**Solo dev complexity:**
- Steep learning curve compared to VN engines or web frameworks
- GDScript is less familiar to AI assistants than Python or TypeScript
- Would need a VN addon (Rakugo/VisualNovelKit) for dialogue/choice UI primitives
- Significant overhead: scene trees, node hierarchies, export templates, input maps
- Massive overkill for a visual novel -- like using Unreal to build a slideshow

**Web deployment:**
- HTML5/WASM export works
- Requires SharedArrayBuffer (cross-origin isolation headers)
- Service worker workaround for CORS
- HTTP threading limitations in web builds

**Verdict:** Godot is a capable engine with good HTTP support, but it's massive overkill for a visual novel. The learning curve is the steepest of any option, GDScript is the least AI-generatable language in the comparison, and you'd spend significant time building VN features that come free with other options. Use Godot if EoQ evolves into a full 2D game with exploration, combat, or physics. For a VN with AI dialogue, it's the wrong tool.

**Sources:**
- [Godot web export documentation](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html)
- [Godot LLM Framework](https://godotengine.org/asset-library/asset/3282)
- [GDLlama - local LLM in Godot](https://github.com/xarillian/GDLlama)
- [Rakugo VisualNovelKit](https://github.com/rakugoteam/VisualNovelKit)
- [Godot LLM integration proposal](https://github.com/godotengine/godot-proposals/issues/13467)

---

### Option 3: Custom Web App (Next.js + React)

**What it is:** A purpose-built web application using modern JavaScript frameworks. The VN presentation layer is React components; the backend is Next.js API routes proxying to vLLM and ComfyUI.

**HTTP API support:**
- **Native and unlimited.** `fetch()`, `axios`, WebSocket, Server-Sent Events -- all first-class browser APIs
- Streaming LLM responses via `ReadableStream` or SSE -- display tokens as they arrive (typewriter effect)
- Next.js API routes proxy requests to vLLM/ComfyUI on the local network, **eliminating CORS entirely**
- WebSocket connection to ComfyUI for real-time generation progress
- Async/await throughout -- no blocking, no freezing

**Dynamic content:**
- Built for dynamic content. React re-renders on state change by definition
- Images load via `<img src={url}>` or `next/image` -- display as soon as ComfyUI returns them
- Text streams into the dialogue box token by token
- No concept of "pre-authored" anything -- everything is data-driven

**State management:**
- Zustand, Redux, React Context, Jotai -- mature ecosystem of state management libraries
- Complex nested state (character vectors, relationship matrices) is trivial in JavaScript objects
- Server-side state in SQLite or PostgreSQL via Next.js API routes
- Qdrant integration for character memory retrieval (already running on Node 1:6333)

**Adult content:**
- Zero restrictions. It's a web page served from your own infrastructure
- No app store review, no platform TOS, no content scanning
- Self-hosted on Athanor -- total control

**Solo dev complexity:**
- React/TypeScript is the language AI assistants (including Claude) generate most fluently
- Next.js is already deployed on Athanor (dashboard at DEV via athanor.local (runtime fallback dev.athanor.local:3001))
- Shaun's orchestrator workflow maps perfectly: describe what you want, AI writes the React components
- VN presentation layer is ~500-1000 lines of React + CSS:
  - Full-screen background image (CSS `background-image`)
  - Character portrait overlay (absolute positioning)
  - Dialogue box at bottom (fixed-position div)
  - Choice buttons (React click handlers)
  - Typewriter text effect (custom hook, ~30 lines)
  - Transitions (CSS transitions or Framer Motion)
- No engine-specific knowledge required beyond web fundamentals

**Web deployment:**
- **Native.** It IS a web app. No export, no compilation, no WASM
- Works in every browser on every device
- Can be a PWA for offline/installable experience
- Can use Tauri or Electron for desktop packaging if ever needed

**Variant: Pixi'VN + React**
Pixi'VN is a TypeScript visual novel engine built on PixiJS with first-class React support. It provides:
- Dialogue system, choice system, character management
- Save/load game state
- Canvas-based rendering (PixiJS) for advanced visual effects
- React template with Zustand state management
- Ink scripting language support (optional)
- Active development (DRincs Productions)
- LGPL-2.1 license

Pixi'VN could accelerate initial development by providing VN primitives out of the box, while still allowing full React/TypeScript customization. The risk is that it's a young project with a small community.

**Verdict:** This is the natural fit. EoQ's core operations -- HTTP API calls, streaming responses, dynamic image display, complex state management -- are exactly what web applications do. React/TypeScript is the most AI-generatable stack. Next.js is already in the Athanor infrastructure. There are no engine limitations to fight. The VN presentation layer is a thin UI skin over what is fundamentally a real-time API client.

**Sources:**
- [Next.js documentation](https://nextjs.org/docs)
- [Pixi'VN engine](https://pixi-vn.web.app/)
- [Pixi'VN React template](https://github.com/DRincs-Productions/pixi-vn-react-template)
- [Zustand state management](https://github.com/pmndrs/zustand)
- [Framer Motion](https://www.framer.com/motion/)

---

### Option 4: Ink/Inkle

**What it is:** A narrative scripting language by Inkle Studios (makers of 80 Days, Heaven's Vault). Ink compiles to JSON, consumed by a runtime (C# or JavaScript via inkjs).

**HTTP API support:**
- None in Ink itself. Ink is a pure narrative logic layer -- no I/O
- All API calls happen in the JavaScript wrapper around inkjs
- Effectively means building a custom web app (Option 3) with an Ink narrative layer in the middle

**Dynamic content:**
- Designed for pre-authored branching narrative
- Variables and conditional logic exist but are for author-defined branches
- An LLM generating dialogue bypasses Ink's branching entirely -- the Ink layer becomes dead weight
- No concept of dynamically generated text flowing through the system

**State management:**
- Ink variables: integers, strings, booleans, lists
- No complex data types (no objects, no arrays, no vectors)
- External functions can bridge to JavaScript, but then you're managing state in JavaScript anyway
- Fundamentally inadequate for personality vectors and relationship matrices

**Adult content:**
- No restrictions in the engine
- Tiny community, almost no adult content ecosystem

**Solo dev complexity:**
- Ink scripting is elegant and easy to learn
- BUT: for EoQ's dynamic content, you'd write the Ink layer AND a full web app wrapper
- Two languages to maintain (Ink + JavaScript/TypeScript) for zero benefit
- AI assistants are mediocre at generating Ink syntax

**Web deployment:**
- inkjs runs natively in browsers -- lightweight and fast
- But Ink only handles narrative logic. You still need a full UI (back to Option 3)

**Verdict:** Ink solves a problem EoQ doesn't have. It's a brilliant tool for hand-authored branching narratives with complex conditional logic. When an LLM generates the dialogue, Ink's branching system is bypassed entirely. You'd build a full web app anyway, then add Ink as dead weight in the middle. Skip it.

**Sources:**
- [Ink GitHub](https://github.com/inkle/ink)
- [inkjs JavaScript port](https://github.com/y-lohse/inkjs)
- [Running your Ink](https://github.com/inkle/ink/blob/master/Documentation/RunningYourInk.md)

---

### Option 5: TyranoScript V6

**What it is:** Web-based visual novel engine, popular in Japan. Games run as HTML5 applications. 20,000+ games created. Free, no commercial restrictions.

**HTTP API support:**
- Built on HTML5/JavaScript -- can use `fetch()` via custom plugins
- Plugin system allows JavaScript extensions
- But no built-in HTTP/API functionality -- must be custom-built
- Tag-based scripting language is awkward for async operations

**Dynamic content:**
- Designed for pre-authored content with tag-based scripting
- Dynamic text insertion via variables is possible
- Dynamic image loading is possible but not a natural pattern
- The tag-based paradigm (`[text]content[/text]`) fights against runtime-generated content

**State management:**
- Tag-based variable system (`[eval]`, `[if]`, `[jump]`)
- Simple typed variables (string, number, boolean)
- No complex data structures
- Inadequate for personality vectors and relationship matrices

**Adult content:**
- No engine restrictions
- Some adult games exist, but community is primarily Japanese
- Smaller English-language adult game community than Ren'Py

**Solo dev complexity:**
- Tag-based scripting is easy for simple VNs
- Documentation is primarily in Japanese (English version improving)
- TyranoStudio (GUI tool) exists but adds another learning surface
- AI assistants have minimal training data on TyranoScript syntax
- Plugin development requires JavaScript knowledge anyway

**Web deployment:**
- Native -- games ARE web pages
- Export to desktop (Electron-based), iOS, Android
- Good multi-platform story

**Verdict:** TyranoScript is web-native, which is good, but its tag-based scripting language is a poor fit for dynamic content and complex state management. The primarily Japanese documentation and small English community make AI-assisted development harder. If you're going to write JavaScript plugins for HTTP calls anyway, you might as well use a JavaScript framework directly.

**Sources:**
- [TyranoScript official site](https://tyranoscript.com/)
- [TyranoBuilder 3.0 update](https://www.nettosgameroom.com/2025/05/tyranobuilder-visual-novel-studio.html)
- [TyranoScript plugin documentation](https://tyranoscript.com/usage/advance/plugin)

---

## Comparison Matrix

| Criterion | Ren'Py 8.5 | Godot 4.4 | Custom Web (Next.js) | Ink/Inkle | TyranoScript V6 |
|-----------|------------|-----------|----------------------|-----------|-----------------|
| **HTTP API calls** | renpy.fetch() -- no streaming | HTTPRequest -- no native streaming | Native fetch/SSE/WebSocket -- full streaming | None (wrapper only) | Plugin-based -- custom work |
| **Streaming LLM text** | Not possible | Requires JS interop hack | Native ReadableStream/SSE | N/A | Not built-in |
| **Dynamic images** | Possible, awkward | Native | Native (`<img>`, `next/image`) | N/A (no rendering) | Possible, awkward |
| **State management** | Python vars, picklable only | Full language, build everything | Zustand/Redux + SQLite/Postgres | Primitives only | Tag-based primitives |
| **Adult content** | No restrictions, huge community | No restrictions, small community | No restrictions, total control | No restrictions, tiny community | No restrictions, Japanese community |
| **AI code generation** | Medium (niche Ren'Py syntax) | Low (GDScript is niche) | **Excellent** (React/TS is #1) | Low (Ink syntax) | Very low (niche + Japanese docs) |
| **Web deployment** | WASM export, networking limits | WASM export, threading limits | **Native web app** | Needs full UI wrapper | Native web app |
| **VN primitives built-in** | **Complete** (best in class) | Needs addon | Must build or use Pixi'VN | None | Complete |
| **Learning curve** | Low (for conventional VN) | High | Medium | Low (narrative only) | Low-Medium |
| **CORS/proxy** | Required, no workaround | Required, service worker hack | **Eliminated via API routes** | N/A | Required |
| **Solo dev overhead** | Low for VN, high for dynamic | Very high | Medium (build VN layer) | Medium (build everything else) | Medium |
| **Infrastructure fit** | Separate deployment | Separate deployment | **Shares Athanor Next.js stack** | Separate deployment | Separate deployment |

---

## Analysis

### The Core Insight

EoQ is not a visual novel. It is a **real-time AI dialogue system with a visual novel presentation layer**. This distinction is critical.

Traditional VN engines (Ren'Py, TyranoScript) are authoring tools. They solve the problem of "I wrote 200,000 words of branching dialogue, help me manage it." EoQ has zero pre-written dialogue. The LLM generates everything at runtime. The hard problem is not narrative branching -- it is HTTP API orchestration, streaming response display, and complex state management.

These are web application problems, not game engine problems.

### Why Ren'Py Almost Works But Doesn't

Ren'Py is the closest traditional VN engine to viable. It has Python scripting, `renpy.fetch()`, and the largest adult VN community. If EoQ were 80% pre-authored content with occasional LLM calls, Ren'Py would be the right choice.

But EoQ is 100% LLM-generated dialogue. The inability to stream responses is a dealbreaker. When a player makes a choice, they'll wait 5-30 seconds for the LLM to generate a response. In a web app, tokens stream in real-time (typewriter effect). In Ren'Py, the screen freezes until the entire response arrives. This is unacceptable UX.

### Why Not Godot

Godot is a fantastic engine for games that need physics, animation systems, tile maps, particle effects, and 2D/3D rendering pipelines. A visual novel needs none of these. Using Godot for EoQ means learning a complex engine, writing everything from scratch via addons, and dealing with a less AI-generatable language (GDScript). The cost-benefit ratio is terrible.

Reserve Godot for if EoQ evolves into a full 2D game with exploration, combat, or spatial mechanics.

### Why Web Wins

Every critical requirement maps to a native web capability:

| EoQ Requirement | Web Solution |
|-----------------|-------------|
| Call vLLM API | `fetch()` or `axios` via Next.js API route |
| Stream LLM tokens | `ReadableStream` or Server-Sent Events |
| Call ComfyUI API | `fetch()` via Next.js API route |
| Monitor ComfyUI progress | WebSocket to ComfyUI `/ws` endpoint |
| Display dynamic images | `<img src={generatedUrl}>` |
| Complex state (vectors, relationships) | Zustand store + SQLite/Postgres |
| Character memory retrieval | Qdrant SDK (already running on Node 1:6333) |
| Save/load game | JSON serialization to server-side storage |
| Cinematic presentation | React components + CSS + Framer Motion |
| Adult content | Self-hosted, no platform restrictions |

No impedance mismatch. No workarounds. No fighting the engine.

---

## Recommendation

### Primary: Next.js + React + Tailwind CSS

Build EoQ as a Next.js web application deployed on Node 2 alongside the existing dashboard.

**Architecture:**

```
Browser (player)
  |
  +---> Next.js App (Node 2, port TBD)
          |
          +-- React UI layer (VN presentation)
          |     - Background component (full-screen scene images)
          |     - Portrait component (character sprites with expressions)
          |     - DialogueBox component (streaming text + speaker name)
          |     - ChoicePanel component (player decision buttons)
          |     - TransitionLayer component (fade, dissolve, etc.)
          |     - HUD component (relationship indicators, scene info)
          |
          +-- State management (Zustand)
          |     - Character store (personality, relationships, emotions)
          |     - World store (location, time, flags, inventory)
          |     - Session store (dialogue history, arc position)
          |     - UI store (current scene, transitions, loading states)
          |
          +-- Next.js API routes (server-side proxy)
                |
                +---> LiteLLM (VAULT:4000) -- dialogue generation
                +---> ComfyUI (Node 2:8188) -- image generation
                +---> Qdrant (Node 1:6333) -- memory retrieval
                +---> SQLite/Postgres -- narrative state persistence
```

**Why Next.js specifically (not plain React/Vite):**
1. API routes eliminate CORS -- the browser talks to Next.js, Next.js talks to vLLM/ComfyUI
2. Server-side state management for save/load and persistence
3. Already in the Athanor stack -- same toolchain, same deployment patterns
4. SSR/ISR for any static content (character bios, world lore pages)
5. App Router with React Server Components for efficient data loading

**VN presentation approach:**
Start with custom React components. The VN UI is approximately 500-1000 lines of React + Tailwind:
- `<SceneBackground>` -- CSS background-image with crossfade transitions
- `<CharacterPortrait>` -- absolute-positioned sprite with expression variants
- `<DialogueBox>` -- bottom-fixed panel with speaker name, streaming text, advance button
- `<ChoicePanel>` -- overlays dialogue box with styled choice buttons
- `<SaveLoadMenu>` -- modal with save slots
- `useTypewriter()` -- custom hook for character-by-character text display from a stream

If rendering needs grow beyond what CSS/DOM can handle (complex layering, particle effects, shader-based transitions), adopt Pixi'VN or raw PixiJS for the canvas layer while keeping React for UI overlays.

**Timeline estimate:**
- Week 1: Project scaffold, VN component library, mock data
- Week 2: vLLM integration (dialogue generation + streaming), state management
- Week 3: ComfyUI integration (scene/portrait generation), image display pipeline
- Week 4: Save/load, narrative state persistence, polish

### Rejected Alternative: Ren'Py with Desktop-First Distribution

If web deployment were not a requirement, Ren'Py would be a defensible choice for desktop distribution. Its `renpy.fetch()` works on desktop without CORS restrictions, the adult VN community is unmatched, and distribution via F95zone/itch.io is well-understood. The streaming limitation remains (poor UX during LLM generation), but desktop Ren'Py could use Python threading to work around it.

This is the fallback if the web approach proves unworkable, but there's no reason to expect it will.

---

## Open Questions

1. **Port allocation:** What port does EoQ run on? (Dashboard is 3001, ComfyUI is 8188, vLLM is 8000)
2. **Monorepo or separate repo?** Could live under `projects/eoq/` or get its own repository
3. **Pixi'VN adoption timing:** Start with plain React, evaluate Pixi'VN if canvas rendering becomes necessary
4. **Character consistency in images:** LoRA training for consistent faces is a separate research topic (see ADR-006)
5. **Mock mode priority:** The ARCHITECTURE.md specifies a mock mode for UI iteration without burning GPU. This should be the first feature built

---

## Sources

### Ren'Py
- [Ren'Py official site](https://www.renpy.org/)
- [renpy.fetch() documentation](https://www.renpy.org/doc/html/fetch.html)
- [Ren'Py web/HTML5 documentation](https://www.renpy.org/doc/html/web.html)
- [Ren'Py GitHub repository](https://github.com/renpy/renpy)
- [renpy-requests patched library](https://github.com/renpytom/renpy-requests)
- [Ren'Py performance at scale](https://mindfulchase.com/explore/troubleshooting-tips/game-development-tools/advanced-ren-py-troubleshooting-memory,-performance,-and-architecture.html)

### Godot
- [Godot web export documentation](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html)
- [Godot LLM Framework addon](https://godotengine.org/asset-library/asset/3282)
- [GDLlama extension](https://github.com/xarillian/GDLlama)
- [Godot LLM Framework GitHub](https://github.com/playajames760/Godot-LLM-Framework)
- [Rakugo VisualNovelKit](https://github.com/rakugoteam/VisualNovelKit)
- [Godot LLM rendering proposal](https://github.com/godotengine/godot-proposals/issues/13467)

### Web / Pixi'VN
- [Pixi'VN engine documentation](https://pixi-vn.web.app/)
- [Pixi'VN React template](https://github.com/DRincs-Productions/pixi-vn-react-template)
- [Pixi'VN GitHub](https://github.com/DRincs-Productions/pixi-vn)
- [Monogatari VN engine](https://monogatari.io/)
- [Monogatari GitHub](https://github.com/Monogatari/Monogatari)
- [react-visual-novel library](https://github.com/utilfirst/react-visual-novel)

### Ink/Inkle
- [Ink GitHub](https://github.com/inkle/ink)
- [inkjs JavaScript runtime](https://github.com/y-lohse/inkjs)
- [Running your Ink documentation](https://github.com/inkle/ink/blob/master/Documentation/RunningYourInk.md)

### TyranoScript
- [TyranoScript official site](https://tyranoscript.com/)
- [TyranoBuilder 3.0 release](https://www.nettosgameroom.com/2025/05/tyranobuilder-visual-novel-studio.html)
- [TyranoScript plugin system](https://tyranoscript.com/usage/advance/plugin)
- [TyranoStudio on Steam](https://store.steampowered.com/app/3634660/TyranoStudio_Visual_Novel_Scripting/)

### Distribution
- [itch.io visual novel category](https://itch.io/games/genre-visual-novel)
- [Ren'Py Steam external patch guide](https://vndev.wiki/Guide:Ren'Py_visual_novels_on_Steam/External_patch)
