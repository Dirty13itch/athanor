# Novel AI Interface Patterns and Interaction Design (2025-2026)

**Date:** 2026-02-25
**Status:** Complete -- comprehensive survey with synthesis
**Scope:** Interface design patterns for an AI agent command center beyond standard dashboards and chatbots
**Context:** Athanor dashboard is Next.js 16 + React 19 + shadcn/ui + Tailwind v4, deployed at DEV via athanor.local (runtime fallback dev.athanor.local:3001) with 16 pages and 26 service health checks. 8 autonomous AI agents, 7 GPUs, media, home automation, creative pipelines. The goal: an interface that feels alive, intuitive, and genuinely novel.

---

## Table of Contents

1. [Conversational UI with Rich Embeds](#1-conversational-ui-with-rich-embeds)
2. [Ambient Computing and Calm Technology](#2-ambient-computing-and-calm-technology)
3. [Spatial Interfaces](#3-spatial-interfaces)
4. [Agent-as-Character](#4-agent-as-character)
5. [Intention-Based Interfaces](#5-intention-based-interfaces)
6. [Timeline and Stream Interfaces](#6-timeline-and-stream-interfaces)
7. [Glanceable Interfaces and Widgets](#7-glanceable-interfaces-and-widgets)
8. [Voice + Visual Multimodal](#8-voice--visual-multimodal)
9. [Feedback Surfaces](#9-feedback-surfaces)
10. [Living and Breathing Interfaces](#10-living-and-breathing-interfaces)
11. [The Single Surface Paradigm](#11-the-single-surface-paradigm)
12. [Novel Synthesis: Composite Concepts for Athanor](#12-novel-synthesis-composite-concepts-for-athanor)
13. [Implementation Roadmap](#13-implementation-roadmap)
14. [Sources](#14-sources)

---

## 1. Conversational UI with Rich Embeds

### The Shift: Conversation as Dashboard

The most significant trend in AI interfaces (2025-2026) is the collapse of the boundary between "chat" and "application." Three paradigms are converging:

**A. Rich Message Blocks (Slack/Discord Model)**

Slack's Block Kit allows up to 50 structured blocks per message: sections, images, dividers, context blocks, input fields, buttons, dropdowns, date pickers, overflow menus, and radio buttons. Each block is a JSON object with a type field. Discord follows a similar pattern with embeds, components (buttons, select menus, text inputs), and modals.

The key insight: these platforms proved that a "message" can be an interactive micro-application. A single message can contain a form, a chart, an approval workflow, or a data table -- and users already understand this mental model from daily work tools.

**B. Canvas/Artifact Model (ChatGPT/Claude)**

ChatGPT Canvas and Claude Artifacts represent the "side panel" approach: the conversation generates a persistent, editable artifact (document, code, diagram, interactive component) that lives alongside the chat. Canvas emphasizes inline editing with surgical precision (highlight and modify specific sections). Artifacts emphasize rendering and visualization (live React components, SVGs, full documents).

The architectural lesson: conversation is the input channel, but the output should be whatever format best serves the content. Text for explanations. Charts for data. Forms for input. Code for... code.

**C. Generative UI (Vercel AI SDK / Google A2UI / AG-UI)**

This is the most relevant paradigm for Athanor. Three protocols/frameworks are emerging:

1. **Vercel AI SDK** (v6, production-ready): The `streamUI` function lets an LLM call tools that return streaming React Server Components. When the model decides it needs to show a chart, it calls a `showChart` tool, and the frontend renders a real React chart component -- not markdown, not an image, a live interactive component. This works with Next.js Server Components and Server Actions natively.

2. **Google A2UI** (v0.8, public preview, Dec 2025): A declarative JSON format where agents describe UI from a trusted component catalog. The host application maintains control over which components are available (security-first design). Agents cannot inject arbitrary code -- they can only reference pre-approved component types like `Card`, `Button`, `TextField`. The same JSON renders across React, Angular, Flutter, or native platforms.

3. **CopilotKit AG-UI Protocol** (production, adopted by Google/LangChain/AWS): An event-based protocol streaming JSON events over HTTP. Event types include `TEXT_MESSAGE_CONTENT`, `TOOL_CALL_START`, `STATE_DELTA` (differential state updates). The `useAgent` React hook subscribes to the event stream and maintains local state. Already adopted by LangGraph, CrewAI, PydanticAI, and others.

### Viability Assessment for Athanor

**High viability.** The Vercel AI SDK approach is immediately implementable because we already run Next.js 16 with React 19 Server Components. The pattern:

1. User sends message to agent via chat panel
2. Agent processes with Qwen3-32B-AWQ via LiteLLM
3. Agent decides response needs a visual component (GPU chart, media gallery, task approval)
4. Agent returns a tool call that maps to a React Server Component
5. Component streams to the client and renders inline in the conversation

This means the chat panel IS the dashboard. "Show me GPU utilization" renders a live chart. "What did the media agent add today?" renders a gallery card with thumbnails. "Approve this model swap?" renders a confirmation card with details and action buttons.

**The key limitation**: Vercel AI SDK's generative UI requires the LLM to reliably call tools. Our Qwen3-32B-AWQ scores 48.71% on BFCL V4, which is mediocre for tool calling. Qwen3.5-27B (~68%) would be significantly better. Alternatively, we can use a hybrid approach: structured intent detection (regex/keyword) to trigger components, with full generative UI as the stretch goal.

### Concrete Components to Build

| Component | Trigger | Renders |
|-----------|---------|---------|
| `GPUStatusCard` | "GPU status", "VRAM usage" | Live GPU grid with utilization bars |
| `AgentActivityCard` | "What did [agent] do?" | Recent activity timeline for that agent |
| `MediaGalleryCard` | "Recent additions", "now playing" | Poster grid from Tautulli/Plex |
| `TaskApprovalCard` | Agent escalation (tier 2/3) | Description + Approve/Reject/Modify buttons |
| `ServiceHealthGrid` | "System health", "service status" | Color-coded service grid |
| `CodeDiffCard` | Coding agent output | Syntax-highlighted diff viewer |
| `ImageGenerationCard` | Creative agent output | Image + prompt + metadata |
| `HomeStatusCard` | "Home status", "lights" | HA entity states, quick toggles |

**Sources:**
- [Slack Block Kit](https://docs.slack.dev/block-kit/)
- [ChatGPT Canvas vs Claude Artifacts](https://xsoneconsultants.com/blog/chatgpt-canvas-vs-claude-artifacts/)
- [Vercel AI SDK 3.0 Generative UI](https://vercel.com/blog/ai-sdk-3-generative-ui)
- [AI SDK RSC: Streaming React Components](https://ai-sdk.dev/docs/ai-sdk-rsc/streaming-react-components)
- [Google A2UI Announcement](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/)
- [A2UI GitHub](https://github.com/google/A2UI)
- [AG-UI Protocol](https://www.copilotkit.ai/ag-ui)
- [CopilotKit v1.50 AG-UI](https://www.marktechpost.com/2025/12/11/copilotkit-v1-50-brings-ag-ui-agents-directly-into-your-app-with-the-new-useagent-hook/)

---

## 2. Ambient Computing and Calm Technology

### Foundational Principles

Mark Weiser and John Seely Brown (Xerox PARC, 1995) coined "calm technology" as computing that "informs but doesn't demand our focus or attention." Amber Case expanded this into eight actionable design principles in 2015:

1. **Minimal attention required** -- technology should require the smallest possible amount of attention
2. **Inform and create calm** -- a person's primary task should not be computing, but being human
3. **Use the periphery** -- move easily from periphery to center of attention and back
4. **Amplify strengths** -- machines shouldn't act like humans; humans shouldn't act like machines
5. **Non-vocal communication** -- not everything needs to speak; consider ambient signals
6. **Graceful failure** -- default to a usable state, never to a broken one
7. **Minimal feature set** -- use only the minimum technology necessary
8. **Respect social norms** -- introduce features gradually, leverage familiar behaviors

### The Tea Kettle Principle

Amber Case's canonical example: a tea kettle is silent while working. It only demands attention when the water is ready. It communicates state change through a single sensory channel (sound) without requiring you to watch it. This is the gold standard for system status communication.

Applied to Athanor: the dashboard should be silent when things are working. The 8 agents, 7 GPUs, 26 services -- when they're healthy, the interface should be calm. Attention should be demanded only when something needs human intervention.

### Peripheral Awareness Displays

Research on ambient displays shows that effective peripheral information uses:

- **Color shifts** -- a background element that shifts from cool blue to warm amber as system load increases
- **Motion presence** -- gentle, almost imperceptible animation when things are active; stillness when idle
- **Spatial position** -- important/urgent items drift toward the center; resolved items drift to edges
- **Sound (sparingly)** -- a single tone for escalation-level events, not for routine updates

### Viability Assessment

**Very high viability.** Calm technology principles should be the *foundation* of Athanor's design, not an add-on feature. The current dashboard has 16 pages with traditional polling-based data display. The redesign opportunity:

- Replace polling-refresh patterns with WebSocket-driven ambient state changes
- Replace "green/red" status indicators with ambient visual treatments (glow, motion, opacity)
- Design the home/overview page as a calm surface that only becomes "loud" when attention is needed
- Use the escalation protocol (already implemented: 3-tier act/notify/ask) to drive UI urgency levels

**Implementation cost: Low.** This is primarily a design philosophy change, not a technical one. CSS transitions, opacity changes, and subtle color shifts are trivial to implement. The hard part is the discipline to *remove* information rather than add it.

**Sources:**
- [Calm Technology Principles - Amber Case](https://www.caseorganic.com/post/principles-of-calm-technology)
- [calmtech.com](https://calmtech.com/)
- [Calm Technology - Wikipedia](https://en.wikipedia.org/wiki/Calm_technology)
- [Mark Weiser, "Designing Calm Technology" (1995)](https://www.semanticscholar.org/paper/Designing-Calm-Technology-Weiser/fdc2e87fcb4575bdf5154840ebd19c2dd490165c)
- [Amber Case, "Calm Technology: Principles and Patterns" (O'Reilly, 2015)](https://www.oreilly.com/library/view/calm-technology/9781491925874/)

---

## 3. Spatial Interfaces

### Beyond Pages: Information in Space

Traditional dashboards use pages, tabs, and navigation menus. Spatial interfaces organize information in a continuous 2D (or 3D) space where position, proximity, and scale carry meaning.

**Zoomable User Interfaces (ZUIs)** -- pioneered by Pad++ (Bederson & Hollan, 1994) -- store all information on a single infinite canvas. Users navigate by panning and zooming. The critical innovation is **semantic zooming**: at different zoom levels, the same object shows different levels of detail. A text document appears as a colored dot when zoomed out, a page thumbnail at medium zoom, and readable text when zoomed in.

**Apple Vision Pro / visionOS** demonstrates spatial computing principles relevant to 2D interfaces:
- Windows as planes in space, freely repositioned
- Content starts in a familiar window and can expand into immersion
- Dynamic scaling ensures content remains clear at any distance
- Comfort-first design: main content stays in the natural field of view

**Canvas/Whiteboard Tools** (tldraw, Excalidraw, Miro, FigJam) show that infinite canvas UIs work on the web:
- tldraw: 44k GitHub stars, React-native, "interactive widgets on the canvas using just React"
- Excalidraw: sketch-aesthetic, end-user focused, lighter weight
- Miro/FigJam: production-proven that spatial arrangement of cards/notes/diagrams works for organizing complex information

### The Spatial Metaphor for Agent Systems

Imagine Athanor's agents as entities arranged in space:

- **Proximity = relevance** -- agents working on related tasks cluster together
- **Size = activity** -- active agents are larger; idle agents are smaller
- **Position = domain** -- creative tools in one region, system tools in another, media in a third
- **Connections = relationships** -- visible lines between agents that are collaborating or delegating
- **Zoom = detail** -- zoom out for overview, zoom into an agent for its activity log, zoom into a task for step-by-step traces

This maps directly to Athanor's architecture: 8 agents, 4 nodes, 7 GPUs, multiple service domains (AI, media, home, creative). The spatial metaphor provides natural organization.

### Practical Considerations

**Research findings on ZUIs (University of Maryland HCI Lab):**
- 80% of subjects prefer overview+detail over pure ZUI for navigation tasks
- However, subjects are *faster* using ZUI, especially with multi-level semantic zoom
- The optimal approach combines: a minimap/overview + semantic zoom on the main canvas

**Performance:** tldraw proves that infinite canvas with real-time React rendering is production-viable on the web. However, rendering dozens of live-updating data visualizations on a canvas simultaneously would need careful performance management (virtualization, off-screen culling).

### Viability Assessment

**Medium-high viability, but high complexity.** A full ZUI would be a significant engineering investment. A more pragmatic approach:

1. **Phase 1**: Use spatial *layout* principles (proximity, clustering, size) within traditional pages. Agent cards arranged spatially rather than in a grid. Size and position driven by activity data.

2. **Phase 2**: Add a "map view" -- a single canvas showing the entire Athanor system with semantic zoom. Start with a simplified representation (nodes, agents, connections) and add detail at zoom levels.

3. **Phase 3** (stretch): Full tldraw-based interactive canvas where agents, tasks, and projects are spatial objects.

**Sources:**
- [Pad++: A Zoomable Graphical Interface System](https://www.cs.umd.edu/~bederson/images/pubs_pdfs/p23-bederson.pdf)
- [Zoomable User Interface (ScienceDirect)](https://www.sciencedirect.com/topics/computer-science/zoomable-user-interface)
- [Navigation patterns and usability of ZUIs (UMD)](http://www.cs.ubc.ca/~tmm/courses/cs533c-02/0310.chrisgray.pdf)
- [tldraw Infinite Canvas SDK](https://tldraw.dev/)
- [Apple visionOS Design Guidelines](https://developer.apple.com/design/human-interface-guidelines/designing-for-visionos)
- [Apple Spatial Layout HIG](https://developer.apple.com/design/human-interface-guidelines/spatial-layout)
- [Zooming User Interface - Wikipedia](https://en.wikipedia.org/wiki/Zooming_user_interface)

---

## 4. Agent-as-Character

### When Anthropomorphism Helps

Research from Frontiers in Computer Science (2025) and PNAS (2025) establishes clear guidelines:

**Beneficial effects:**
- Highly anthropomorphic avatars correlate with elevated empathy and trust
- Emotional engagement matters more than perceived intelligence for user experience
- Visual identity (avatar, color, icon) helps users build mental models of agent capabilities
- In tutoring/coaching/mentoring contexts, anthropomorphism improves outcomes

**Counterproductive effects:**
- Anthropomorphism risks misleading users about actual capabilities (the "uncanny expectations" problem)
- A "dehumanization paradox" -- exposure to socio-emotional AI can lead people to perceive other humans as less human
- When perceived intelligence exceeds actual capability, trust collapses harder than if expectations were lower

**The sweet spot for Athanor:** Visual identity and personality indicators (names, colors, icons, status) without pretending agents are people. The agents have distinct roles, capabilities, and behavioral patterns -- represent those honestly. Think "team of specialized tools with distinct identities" rather than "team of people."

### Lessons from Games

RPG companion systems offer decades of design research:

**Portrait + Status Bar (Baldur's Gate, Dragon Age):** Each companion has a portrait showing their current state, a health/status bar, and condition indicators. The portrait is always visible in the HUD. This is the "glanceable companion status" pattern -- you know at a glance who's healthy, who's struggling, who's active.

**Approval/Relationship Indicator (Mass Effect, Dragon Age):** Companions have a relationship meter that changes based on your decisions. Applied to Athanor: an agent's "satisfaction" or "confidence" indicator -- how well is it performing? Is it getting good feedback? Is it struggling with tasks?

**Mood/State Animation (many RPGs):** Companion portraits change expression based on context. A worried companion shows a different portrait during danger. Applied to Athanor: agent cards that visually reflect operational state -- calm when idle, focused when processing, alert when escalating.

### Concrete Design: Agent Identity System

| Agent | Color | Icon | Personality Indicator |
|-------|-------|------|----------------------|
| General Assistant | Warm amber | Flame/furnace | The alchemist's apprentice -- steady, reliable |
| Media Agent | Deep purple | Film reel | The librarian -- organized, acquisitive |
| Research Agent | Teal | Compass/telescope | The scholar -- thorough, curious |
| Creative Agent | Magenta/rose | Palette/brush | The artist -- expressive, generative |
| Knowledge Agent | Forest green | Book/graph | The archivist -- systematic, connecting |
| Home Agent | Soft blue | House/lightbulb | The steward -- attentive, responsive |
| Coding Agent | Electric blue | Terminal/brackets | The engineer -- precise, iterative |
| Stash Agent | Dark red | Lock/eye | The curator -- discreet, organized |

Each agent card shows:
- **Identity**: Name, icon, color accent
- **Status pulse**: Idle (dim, still), Active (bright, gentle pulse), Escalating (amber glow, faster pulse)
- **Last action**: One-line summary of most recent activity
- **Health indicator**: Success rate trend (up/down/stable arrow)
- **Current task**: If processing, what it's working on

### Viability Assessment

**High viability, moderate design effort.** The technical implementation is straightforward (React components with conditional styling). The design effort is in creating a coherent visual identity system that feels intentional rather than arbitrary. This should be done as part of the broader design system refresh, not as an isolated feature.

**Sources:**
- [Effect of anthropomorphism in chatbot avatars (Frontiers, 2025)](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1531976/full)
- [Benefits and dangers of anthropomorphic agents (PNAS, 2025)](https://www.pnas.org/doi/10.1073/pnas.2415898122)
- [Game UI Database - Object/NPC Information](https://www.gameuidatabase.com/index.php?scrn=164)
- [Mastering Game HUD Design (Polydin)](https://polydin.com/game-hud-design/)

---

## 5. Intention-Based Interfaces

### The Command Palette Revolution

Raycast, Alfred, Spotlight, and now PowerToys Command Palette have proven that a single input field with fuzzy matching is the fastest way to navigate complex systems. The pattern: press a hotkey, type what you want, get results.

What makes modern command palettes different from traditional search:
- **Context awareness**: Raycast works with selected text, clipboard content, and screen state
- **Action-oriented**: Results aren't just links -- they're executable actions
- **Extensible**: Plugins add new commands dynamically
- **AI-enhanced**: Natural language understanding maps intent to actions

### Context-Aware Self-Assembling Interfaces

David vonThenen's "Invisible by Design" (2025) describes a four-layer data model for context-aware interfaces:

1. **Macro context**: Regional/system-wide patterns (GPU utilization trend, agent load distribution)
2. **Micro context**: Local conditions (current page, recent interactions, time of day)
3. **Personal context**: User preferences (which agents you interact with most, preferred detail level)
4. **Real-time context**: Current activity (what you're working on right now)

The system fuses these into a unified context model and uses it to pre-assemble the right interface before you ask. The success metric is **"time-to-intent"** -- how fast you go from conceiving a goal to achieving it.

### Applied to Athanor: Intent Mode

Imagine typing "EoBQ" into a command palette. Instead of navigating to a project page, the entire interface reorganizes:

- Agent cards reorder: Creative Agent and Coding Agent become primary
- The activity timeline filters to EoBQ-related events
- GPU status highlights the GPUs running creative workloads
- Quick actions change to EoBQ-relevant operations (generate scene, compile build, review assets)
- The "focus" persists until explicitly dismissed or a new intent is declared

This is not a search. It is a contextual lens that reshapes the entire interface.

**Implementation approach:**
1. Command palette (Cmd+K / Ctrl+K) with fuzzy matching over agents, services, projects, actions
2. "Focus mode" that filters and reorganizes all visible components based on declared intent
3. Agent-backed intent resolution: the general assistant interprets natural language intent and maps it to UI state
4. Persistent focus context stored in user preferences (the agent preference system already supports this)

### Viability Assessment

**High viability, high value.** A command palette is a weekend build with existing shadcn/ui components (shadcn has a `CommandDialog` component). Focus mode requires a React context provider that all components read from. The natural language intent resolution can leverage the existing agent framework.

This is arguably the single highest-impact interaction improvement for a power user like Shaun. One keyboard shortcut to reach anything in the system, plus contextual reorganization.

**Sources:**
- [Invisible by Design: Context-Aware Interfaces (vonThenen, 2025)](https://davidvonthenen.com/2025/09/10/invisible-by-design-context-aware-interfaces-that-assemble-themselves/)
- [Command Palette Interfaces (Fountn)](https://fountn.design/resource/command-palette-interfaces/)
- [Designing a Command Palette (Destiner)](https://destiner.io/blog/post/designing-a-command-palette/)
- [Nailing Command Palette Activation (Multi)](https://multi.app/blog/nailing-the-activation-behavior-of-a-spotlight-raycast-like-command-palette)
- [Raycast AI: AI-Native OS](https://skywork.ai/skypage/en/Raycast-AI-The-Ultimate-Guide-to-an-AI-Native-OS/1975270466257612800)

---

## 6. Timeline and Stream Interfaces

### Activity Feed as Primary Navigation

The activity stream pattern (well-established in social platforms, project management tools, and monitoring systems) treats time as the primary axis of organization. Everything that happens flows through a chronological feed.

**Key design decisions for activity streams:**

| Decision | Options | Recommendation for Athanor |
|----------|---------|---------------------------|
| Ordering | Chronological / Reverse-chrono / Ranked | Reverse-chronological (most recent first) with pinning for escalations |
| Grouping | By time / By agent / By domain | Time-based with agent attribution (colored left border matching agent identity) |
| Density | Compact / Standard / Expanded | Multi-density: compact by default, expand on click/hover, full detail on navigate |
| Filtering | Tags / Source / Type | Agent filter + event type filter (action/escalation/completion/error) |
| Interactivity | Read-only / Actionable | Actionable -- approve, dismiss, respond inline |

**The social media insight:** Twitter/Instagram proved that a well-designed feed is addictive because it combines discovery (what's new?) with agency (I can react). Apply this to Athanor: the activity stream should feel like scrolling through what your AI team accomplished, with the ability to react, redirect, or dig deeper at any point.

### Event Sourcing as Backend Pattern

Athanor already has the backend for this: activity logging to Qdrant's `activity` collection on every chat completion, task execution logs with step-by-step traces, and GWT workspace events via Redis pub/sub. The activity stream UI is a natural frontend for this existing event infrastructure.

The event sourcing pattern (append-only store recording all state changes) maps perfectly: every agent action, every task completion, every escalation is an event. The timeline is just a view over the event store.

### Design Patterns from Activity Feeds

From GetStream and Aubergine's research on chronological activity feeds:

- **Rich previews**: Show enough context to understand without clicking (agent name, action summary, result thumbnail)
- **Inline actions**: "Approve", "Dismiss", "Reply" buttons directly on feed items
- **Grouped notifications**: Multiple related events collapsed into one entry ("Creative Agent generated 4 images for EoBQ" instead of 4 separate entries)
- **Read/unread state**: Visual distinction between new and seen events
- **Anchored time markers**: "2 hours ago", "Yesterday", "This week" section headers

### Viability Assessment

**Very high viability.** The data already exists. The backend APIs already exist (`GET /v1/tasks`, activity collection in Qdrant). This is a pure frontend build on existing infrastructure. A well-designed activity stream could replace the current separate Activity and Tasks pages with a unified, more useful view.

**Sources:**
- [Activity Stream Design Pattern (ui-patterns.com)](https://ui-patterns.com/patterns/ActivityStream)
- [Guide to Designing Chronological Activity Feeds (Aubergine)](https://www.aubergine.co/insights/a-guide-to-designing-chronological-activity-feeds)
- [Activity Feed Design Guide (GetStream)](https://getstream.io/blog/activity-feed-design/)
- [Event Sourcing Pattern (Martin Fowler)](https://martinfowler.com/eaaDev/EventSourcing.html)

---

## 7. Glanceable Interfaces and Widgets

### Apple's Widget Design Doctrine

Apple's Human Interface Guidelines for widgets represent the most thoroughly researched set of glanceable design principles:

- **Glanceability is the measure**: People spend ~10 seconds max engaging with a widget
- **Widgets are not mini-apps**: They project content from an app onto a surface
- **Information density scales with size**: Smallest widget = one key metric. Largest = 3-4 pieces of information
- **No interaction complexity**: A widget has one tap target (the whole widget), not multiple buttons
- **Timeliness**: Show the most relevant information for *right now*, not comprehensive data

### Smart Stack and Contextual Surfacing

watchOS 10's Smart Stack automatically reorders widgets based on time, location, and usage patterns. A weather widget surfaces in the morning; a meeting widget surfaces before appointments. This is calm technology in action: the right information appears when relevant without being requested.

Applied to Athanor: widgets on the home page that reorder based on context:
- During EoBQ work sessions: Creative Agent status and GPU utilization surface to top
- During evening: Media (now playing) and Home Agent surface
- When an escalation occurs: the escalating agent's widget jumps to top with amber glow
- During system maintenance: Service health and node status surface

### Layout Patterns from Apple Watch

Apple defines several widget layout archetypes:

| Layout | Use Case | Athanor Analog |
|--------|----------|----------------|
| **Large text** | Single metric | "4 tasks running" or "99.1% uptime" |
| **Bar gauge** | Progress/range | GPU VRAM utilization bar |
| **Circular graphic** | Multi-metric ring | Agent activity rings (like Apple Activity) |
| **Icon + text** | Status + label | Agent name + current status |
| **Grid** | Multiple related items | 4-GPU mini-status |

### Information Density Research

The critical constraint: **what information can Shaun absorb in 2 seconds?** Research on information density in dashboards (Stephen Few, "Information Dashboard Design") establishes:

- 5-7 distinct data points is the maximum for a single glance
- Color is processed pre-attentively (faster than text) -- use it for status
- Position is processed pre-attentively -- use spatial layout for grouping
- Size differences must be >30% to be reliably distinguished
- Animation catches attention involuntarily -- use sparingly, only for things that *should* catch attention

### Viability Assessment

**Very high viability.** This maps directly to shadcn/ui card components with conditional styling. The implementation is:

1. Define widget component library (small/medium/large sizes with semantic variants)
2. Each widget fetches one data source and renders one glanceable view
3. Home page is a responsive grid of widgets
4. Widget ordering driven by a priority function (time of day, active focus, escalation state)

This is the foundation layer -- every other concept builds on top of well-designed glanceable components.

**Sources:**
- [Apple HIG: Widgets](https://developer.apple.com/design/human-interface-guidelines/widgets/)
- [Design Great Widgets (WWDC20)](https://developer.apple.com/videos/play/wwdc2020/10103/)
- [Design Widgets for Smart Stack (WWDC23)](https://developer.apple.com/videos/play/wwdc2023/10309/)
- [iOS Widget Design Handbook (Design+Code)](https://designcode.io/ios-design-handbook-design-widgets/)

---

## 8. Voice + Visual Multimodal

### The Multimodal Promise

Multimodal interfaces combine voice commands with visual feedback: "Show me what the creative agent made today" triggers a visual gallery. The interaction is voice-first, but the response is visual.

Key principles from 2025 multimodal design research:

- **Modality should match context**: Voice-first when hands are busy (morning routine, cooking). Touch-first on phone. Visual-first at desk.
- **Fluid transitions**: A user may start with a gesture, continue with speech, and finish with visual confirmation. Design the choreography.
- **Visual confirmation of voice**: Always show what was heard/understood. Build confidence that the system understood correctly.
- **Progressive disclosure**: Voice command shows summary; visual display provides detail.

### Applied to Athanor

Athanor already has the voice infrastructure: wyoming-whisper (STT), wyoming-piper (TTS), speaches API, "Athanor Voice" pipeline in Home Assistant with wake word detection. The missing piece is visual response integration.

The flow:
1. "Hey Athanor, what's the GPU status?" (captured by wake word + STT)
2. HA automation triggers agent API call
3. Agent responds with text + structured data
4. Dashboard receives push notification via WebSocket
5. Dashboard renders GPU status card in the foreground
6. TTS reads a summary: "All 7 GPUs active. Foundry running inference at 23% utilization. Workshop creative pipeline idle."

This requires a new integration: HA voice pipeline results pushing structured data to the dashboard via WebSocket, triggering appropriate visual components.

### Viability Assessment

**Medium viability today, high viability after voice pipeline maturation.** The voice infrastructure exists but the "voice command -> structured visual response" pipeline needs engineering. The HA->WebSocket->dashboard path is the implementation gap.

For now, voice and visual are parallel channels. Making them truly multimodal (voice triggers visual, visual enhances voice) is a medium-term goal.

**Sources:**
- [Voice UX Design & Multimodal Interfaces (Payoda)](https://www.payoda.com/voice-ux-design-multimodal-voice-interfaces-explained/)
- [Designing Multimodal AI Interfaces (FuseLab)](https://fuselabcreative.com/designing-multimodal-ai-interfaces-interactive/)
- [VUI Design Principles 2026 (ParallelHQ)](https://www.parallelhq.com/blog/voice-user-interface-vui-design-principles)
- [Multimodal Interfaces: Voice, Vision & AI (BlendX)](https://blendx.design/blogs/multimodal-interfaces-merging-voice-vision-ai-to-elevate-user-engagement/)

---

## 9. Feedback Surfaces

### Beyond Thumbs Up/Down

Google's People + AI Research (PAIR) guidelines identify five levels of feedback communication, from weakest to strongest:

1. Simple acknowledgment ("Thanks")
2. Broad improvement ("helps us improve")
3. Personalized scope ("improves your recommendations")
4. Specific changes ("won't include X anymore")
5. **Immediate demonstration** ("we've updated -- take a look")

Level 5 is the goal: when you give feedback, the system immediately shows you the effect.

### A Taxonomy of Feedback Types (CHI 2025)

Recent research (CHI Conference on Human Factors 2025) identifies feedback beyond the explicit/implicit binary:

- **Explicit feedback**: Deliberate rating actions (thumbs up, stars, written review)
- **Intentional implicit feedback**: Behaviors consciously performed by users expecting the system to interpret them (saving an item, spending extra time viewing, copying text)
- **Unintentional implicit feedback**: Behavioral signals users don't realize they're sending (scroll speed, time-on-page, mouse movement patterns, undo frequency)

The most powerful signal identified: **the undo**. When a user accepts output and immediately reverts, that's the loudest possible negative signal.

### Feedback Surfaces for Athanor

**A. Inline Micro-Feedback on Agent Output**

Every agent response in the activity stream or chat gets:
- Quick reaction buttons: a small thumbs up, thumbs down, or "not relevant" -- rendered as subtle icons, not prominent buttons
- "More like this" / "Less like this" -- for creative outputs (images, video), media recommendations
- "Show me your reasoning" -- expand to see the agent's decision chain
- Natural language micro-correction: a small inline text field for "Actually, I meant..." responses

**B. Behavioral Signals (Implicit)**

Track without asking:
- Which agent outputs does Shaun expand vs. skip?
- Which widgets does he interact with most?
- How long does he spend on different pages?
- Which escalations does he approve vs. reject vs. modify?
- What times of day does he interact with what domains?

These feed back into agent context injection (the `context.py` module already injects preferences) and widget priority ordering.

**C. Preference Capture Through Interaction**

The preference system (Qdrant `preferences` collection) already exists. The feedback surface should make preference capture feel natural:

- Dismissing a notification teaches "don't notify me about this"
- Expanding an agent's detail teaches "I care more about this agent"
- Rearranging widgets teaches layout preference
- Adjusting a refresh interval teaches information density preference

### Viability Assessment

**High viability.** The preference storage infrastructure exists. Inline micro-feedback is a UI component exercise. Behavioral tracking requires a lightweight analytics layer (event listeners on key interactions, batched writes to the `preferences` collection).

The discipline is in restraint: capture feedback without making the interface feel like a survey. Every feedback surface should feel like a natural part of the interaction, not an interruption.

**Sources:**
- [Feedback + Control (Google PAIR)](https://pair.withgoogle.com/chapter/feedback-controls/)
- [Beyond Explicit and Implicit Feedback (CHI 2025)](https://dl.acm.org/doi/full/10.1145/3706598.3713241)
- [Beyond Thumbs Up/Down: Fine-Grained Feedback (arXiv)](https://arxiv.org/html/2406.16807)
- [Feedback by Design: User Feedback Barriers (arXiv, 2025)](https://arxiv.org/html/2602.01405v1)
- [Silent Signals: Future of AI Learning (DEV Community)](https://dev.to/mosiddi/stop-begging-for-feedback-why-silent-signals-are-the-future-of-ai-learning-40jp)

---

## 10. Living and Breathing Interfaces

### Data-Driven Animation

The 2026 motion design trend is "smart motion" -- animation that carries meaning, responds to behavior, and communicates system state rather than just providing visual polish.

**LottieFiles state machines** allow animations to change based on logic -- an animation has multiple states (idle, active, error, success) and transitions between them based on data. This is directly applicable: an agent icon that has different animation states based on its operational status.

**Motion (formerly Framer Motion)** is the production React animation library with:
- Physics-based springs for natural-feeling transitions
- Layout animations (components smoothly reflow when data changes)
- Gesture-driven animations (drag, hover, tap)
- Shared layout animations (elements morph between states)
- `variants` for declarative animation state machines

### The "Breathing" Metaphor

A breathing interface subtly communicates system vitality:

- **System idle**: Slow, gentle pulsing (4-6 second cycle) on accent elements. Like a sleeping animal's breathing.
- **System active**: Slightly faster rhythm (2-3 second cycle), warmer color temperature
- **System stressed**: Faster pulse, amber/orange shift, increased contrast
- **System error**: Sharp attention-grabbing animation, red accent, stops only on acknowledgment

Implementation with CSS:
```css
@keyframes breathe {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.02); }
}

.system-pulse {
  animation: breathe var(--breath-speed, 4s) ease-in-out infinite;
}
```

The `--breath-speed` CSS custom property is driven by a data attribute that reflects system load. JavaScript updates the property based on Prometheus metrics. No complex animation library needed for the base effect.

### Ambient Status Through Visual Treatment

Beyond animation, static visual properties communicate state:

| State | Background | Border | Text | Glow |
|-------|------------|--------|------|------|
| Healthy/idle | Dark, muted | None or subtle | Dim | None |
| Active/processing | Slightly warmer | Agent color, thin | Normal | Subtle agent color |
| Attention needed | Warm amber tint | Amber, thicker | Bright | Warm amber |
| Error/critical | Dark red tint | Red | High contrast | Red pulse |

The key principle: **changes in visual treatment catch attention.** A card that was dim and suddenly becomes warm will be noticed without any explicit notification. This is calm technology: the interface itself *is* the notification system.

### Generative and Data-Driven Visuals

More ambitious concepts:

- **Particle systems**: A background particle field whose density and motion reflects system activity. Dense, fast particles when many tasks are running. Sparse, slow when idle. This is technically feasible with WebGL/Three.js but high on GPU cost for a dashboard.

- **Generative patterns**: Background patterns generated from system metrics. CPU utilization drives pattern complexity. Memory pressure drives pattern density. Artistically interesting and informatively useful, but high design complexity.

- **Heat map overlays**: Subtle color gradients behind agent cards showing their recent activity intensity. No explicit chart -- just the card's background shifts warmer when the agent has been busy.

### Viability Assessment

**High viability for CSS-based ambient effects. Medium viability for Motion animations. Low viability for generative/particle systems.**

The pragmatic path:
1. CSS custom properties driven by system metrics (breathing, color temperature, opacity)
2. Motion library for state transitions (agent cards animating between states, layout reflow when widgets reorder)
3. Skip generative/particle systems -- they add visual complexity without proportional information value, and they consume CPU/GPU on the dashboard machine

**Sources:**
- [Motion UI Trends 2026 (LoMA Technology)](https://lomatechnology.com/blog/motion-ui-trends-2026/2911)
- [Motion.dev (formerly Framer Motion)](https://motion.dev)
- [React Animation with Motion](https://motion.dev/docs/react-animation)
- [Generative UI (Google Research)](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
- [Generative UI: The AI-Powered Future (Medium)](https://medium.com/@knbrahmbhatt_4883/generative-ui-the-ai-powered-future-of-user-interfaces-920074f32f33)

---

## 11. The Single Surface Paradigm

### One Surface, Many Depths

The "single surface" paradigm replaces pages/tabs/navigation with one continuous surface. You don't go *to* the GPU page -- you zoom *into* the GPU region. You don't navigate *to* an agent -- you focus *on* that agent. The mental model shifts from "collection of pages" to "territory of information."

**Research findings:**

- Pad++ (Bederson, UMD) demonstrated that semantic zooming works for document collections, code, and data visualization
- Prezi proved that non-linear, spatial presentation works for mass audiences
- 80% of users prefer having a minimap/overview alongside the zoomable surface
- Users are *faster* with ZUI for navigation tasks vs. traditional menus
- The critical success factor is **orientation** -- users must always know where they are in the overall space

### How Semantic Zoom Would Work for Athanor

**Level 0 -- Full Overview (max zoom out)**:
- The entire system as a single view
- Nodes as colored rectangles (green = healthy, amber = attention, red = error)
- Agents as small dots within their host node, color-coded
- Connections between nodes as lines (thicker = more traffic)
- A single health metric per node (CPU%, memory%)
- GPU utilization as tiny bar charts within node rectangles

**Level 1 -- Domain View (medium zoom)**:
- Agents become cards with name, status icon, and last action
- Nodes show expanded metrics (CPU, RAM, GPU, network, storage)
- Services visible as labeled dots within nodes
- Active tasks visible as animated connections between agents

**Level 2 -- Entity Detail (high zoom)**:
- Full agent detail: activity log, current tasks, configuration, performance metrics
- Full node detail: all services, container status, resource graphs
- Full task detail: step-by-step execution trace, input/output, duration

**Level 3 -- Deep Dive (max zoom in)**:
- Individual log entries
- Raw API responses
- Configuration files
- Model parameters

### Practical Implementation Challenges

1. **Performance**: Rendering all zoom levels simultaneously is expensive. Need aggressive virtualization: only render what's visible at the current zoom level.

2. **Navigation**: Without familiar page URLs and back buttons, users can get lost. Need: breadcrumb trail, minimap, "home" shortcut (zoom to overview).

3. **Deep linking**: How do you share "the agent detail view for the creative agent"? URL encoding of viewport position + zoom level.

4. **Mobile**: Pinch-to-zoom is natural on mobile, but the screen is too small for meaningful overview + detail simultaneously.

5. **Incremental adoption**: This is an all-or-nothing paradigm shift. Hard to adopt incrementally alongside traditional pages.

### Viability Assessment

**Low viability as a primary interface. Medium viability as an optional "system map" view.**

The single-surface paradigm is intellectually elegant but practically challenging for a primary interface. The implementation cost is very high (essentially building a custom rendering engine), and the benefit over well-designed pages with fast navigation (command palette) is marginal for a single user.

However, a simplified "system map" -- a single canvas showing nodes, agents, and their relationships at one zoom level, with click-to-detail -- is a compelling addition alongside traditional pages. Think of it as the "overview tab" rather than the replacement for everything.

**tldraw could serve as the foundation** for a system map view. It handles pan/zoom, rendering, and interactivity. Custom shapes (agent cards, node rectangles) are supported. The question is whether the engineering investment justifies the benefit for a single-user system.

**Sources:**
- [Zoomable User Interface (ScienceDirect)](https://www.sciencedirect.com/topics/computer-science/zoomable-user-interface)
- [Pad++ Paper (UMD)](https://www.cs.umd.edu/~bederson/images/pubs_pdfs/p23-bederson.pdf)
- [Navigation patterns and usability of ZUIs (UMD)](http://www.cs.umd.edu/hcil/trs/2001-11/2001-11.html)
- [Zooming User Interface - Wikipedia](https://en.wikipedia.org/wiki/Zooming_user_interface)

---

## 12. Novel Synthesis: Composite Concepts for Athanor

The individual patterns above are well-studied. The novel part is combining them into something purpose-built for an autonomous AI agent command center. Here are five composite concepts, each combining 3+ patterns.

### Concept A: "The Furnace" -- A Living Home Surface

*Combines: Calm Technology + Living/Breathing UI + Glanceable Widgets + Agent-as-Character*

The dashboard home page is not a grid of panels. It is a living surface -- a dark, warm canvas that breathes with the rhythm of the system. The Athanor brand aesthetic (Cormorant Garamond, amber warmth, dark minimalism) is not decoration; it is data visualization.

**The surface itself communicates:**
- Background warmth (color temperature) reflects overall system activity. Cool/dark when idle. Warmer when busy. The furnace metaphor -- the athanor glows when it's working.
- A subtle ambient glow at the edges of the screen shifts based on system health. Healthy = barely visible. Attention needed = warm amber creeping inward. Critical = impossible to ignore.
- The central area is nearly empty when everything is fine. Information *appears* when it's relevant and *fades* when it's resolved. Calm technology: the best state is near-emptiness.

**Agent presence:**
- Each agent is represented as a small ember/flame icon in its signature color, arranged in a gentle arc or constellation
- Active agents pulse gently. Idle agents are dim but present. Escalating agents glow brighter and drift toward center
- Hovering over an agent shows a tooltip: name, status, last action
- Clicking opens a card with full detail (slides in from the side, doesn't replace the surface)

**Contextual surfacing (Smart Stack):**
- 2-3 widget cards float on the surface, auto-selected based on relevance:
  - Morning: upcoming calendar + weather + agent overnight summary
  - Work session: active project metrics + relevant agents + GPU status
  - Evening: media now playing + home status
  - Escalation: the escalating agent's card replaces everything until resolved

**Why this works:** It honors the athanor metaphor from VISION.md. The furnace is always running, but you only open the door to check when something needs attention. The surface IS the monitoring system. No need to scan dashboards -- the dashboard tells you when to look.

**Technical requirements:**
- CSS custom properties driven by WebSocket-pushed system metrics
- Motion library for agent icon states and widget transitions
- Smart Stack priority algorithm (time of day + user behavior + escalation state)
- ~2-3 weeks of focused implementation

---

### Concept B: "The Stream" -- Conversation as Command Center

*Combines: Conversational UI + Rich Embeds + Timeline/Stream + Generative UI*

The primary interface is a single, unified stream. Not a chat interface. Not an activity feed. A hybrid: an intelligent stream that interleaves agent activity, system events, and user conversation in one continuous flow.

**The stream contains:**
- Agent activity entries: "Creative Agent generated 3 images for EoBQ scene 4" (with thumbnail gallery inline)
- System events: "Node 1 GPU utilization peaked at 87% during batch inference" (with mini spark chart inline)
- User messages: "Focus on EoBQ tonight" (triggers intent mode, acknowledged inline)
- Escalation cards: "Media Agent wants to reorganize the anime library. Approve?" (with approve/reject/modify buttons inline)
- Agent conversations: Full chat exchanges appear as threaded entries in the stream
- Task completions: "Coding Agent completed code review (4 files, 2 suggestions)" (with diff preview inline)

**Rich embeds powered by Vercel AI SDK:**
When you type a message, the general assistant processes it and can return:
- Pure text (normal response)
- A React component (GPU chart, media gallery, task status board)
- An action card (approval request, confirmation dialog)
- A redirect (agent delegation: "The creative agent will handle this")

**The stream replaces multiple pages:** Activity, Tasks, Chat, and Notifications all collapse into one chronological view with filtering. The filter bar at the top offers: All | Agents | System | Chat | Escalations.

**Threading:** Complex interactions expand into threads (like Slack). A task that took 10 steps is one entry in the main stream with a "10 steps" link that expands into the full trace.

**Why this works:** It mirrors how Shaun already interacts with the system -- through conversation and activity monitoring. Instead of switching between chat and dashboard pages, everything flows through one surface. The stream is the single source of truth for "what happened and what needs attention."

**Technical requirements:**
- Unified event model (merge agent activity + system events + chat messages)
- Vercel AI SDK for generative UI components in chat responses
- WebSocket for real-time stream updates
- Virtual scroll for performance (potentially hundreds of entries per day)
- Rich component library for inline embeds (charts, galleries, diffs, approval cards)
- ~4-6 weeks of focused implementation

---

### Concept C: "The Lens" -- Intent-Driven Adaptive Interface

*Combines: Intention-Based Interface + Spatial Layout + Feedback Surfaces + Ambient Computing*

The dashboard is always the same URL, but what it shows depends on the current "lens" -- a declared intent that reshapes everything.

**Default lens (no focus):**
- The Furnace surface (Concept A) -- calm, ambient, glanceable
- Agent constellation, contextual widgets, breathing ambient state

**Project lens (e.g., "EoBQ"):**
- Agents reorder: Creative Agent and Coding Agent become primary, large cards
- Activity stream filters to EoBQ-related events
- Quick actions change: "Generate scene", "Review assets", "Compile build"
- GPU status highlights creative workloads
- Right panel shows project-specific metrics (scene count, asset inventory)

**Agent lens (e.g., focusing on Creative Agent):**
- That agent's card expands to fill the main area
- Full activity history, current tasks, performance metrics
- Configuration panel accessible
- Other agents become small, peripheral
- Quick actions are agent-specific: "Generate image", "Change model", "View gallery"

**Domain lens (e.g., "Media"):**
- Media Agent card expands
- Plex now playing, recent additions, library health
- Sonarr/Radarr queue status
- Tautulli analytics
- Quick actions: "Scan library", "Search", "Request"

**System lens (e.g., "Health check"):**
- Node cards with full metrics
- Service health grid
- GPU utilization charts
- Active alerts and warnings
- Quick actions: "Restart service", "Clear cache", "Run backup"

**Lens activation:**
- Command palette (Cmd+K): type to search and activate any lens
- Agent card click: activates that agent's lens
- Widget click: activates the relevant domain lens
- Voice: "Focus on EoBQ" activates project lens
- Auto-detection: if you're on a project page in another tool, the dashboard could detect it (stretch goal)

**Feedback loop:** The system learns which lenses you use, when, and for how long. Over time, the Smart Stack prioritizes widgets and the default surface adapts to your patterns.

**Why this works:** It solves the "16 pages" problem. Instead of navigating between 16 pages, you have one adaptive surface that shows what matters for your current intent. Navigation becomes declaration of intent rather than spatial movement through menus.

**Technical requirements:**
- Lens state manager (React context + URL query param for bookmarkability)
- Per-lens layout definitions (which components, what size, what order)
- Command palette with lens activation
- Smooth layout transitions (Motion library)
- ~3-4 weeks for core, ongoing refinement

---

### Concept D: "The Crew" -- Agent Team Interface

*Combines: Agent-as-Character + Game HUD Patterns + Feedback Surfaces + Timeline/Stream*

Inspired by RPG party management screens, this concept treats the 8 agents as a team with individual identities, specialties, and performance histories.

**The Crew View:**
A horizontal row of agent portraits at the bottom of the screen (always visible, like an RPG party bar). Each portrait is a ~48px circle with the agent's color and icon. Visual states:

| State | Visual Treatment |
|-------|-----------------|
| Idle | Dim, static |
| Processing | Gentle pulse in agent color |
| Success | Brief bright flash, then settle |
| Failed | Brief red flash, then amber idle |
| Escalating | Continuous amber pulse, slightly larger |
| Disabled | Greyed out, smaller |

**Agent Detail Panel (click on portrait):**
Slides up from the bottom (like a game character sheet):
- **Identity header**: Name, role, icon, color
- **Stats**: Tasks completed (today/week/all-time), success rate, avg response time
- **Current task**: If active, what it's doing with progress indication
- **Recent activity**: Last 5 actions with outcomes
- **Relationship**: Which agents it delegates to / receives from (shown as connections)
- **Feedback history**: Your recent thumbs up/down on its outputs
- **Performance trend**: Sparkline of success rate over last 7 days

**Team Dynamics:**
- When agents collaborate (e.g., general assistant delegates to coding agent), a brief connection animation flashes between their portraits
- Agents that frequently work together are positioned closer in the portrait bar
- An agent that's been performing well gets a subtle "level up" indicator (a small star or brightness increase)

**Why this works:** It makes the abstract concept of "8 AI agents" tangible and relatable. Instead of a list of services, you have a team you can observe, direct, and evaluate. The RPG metaphor gives Shaun (a gamer) an intuitive mental model.

**Technical requirements:**
- Agent portrait component with state-driven animation
- Agent detail panel with stats aggregation from activity/task data
- Portrait bar component (persistent across all views)
- Connection animation between collaborating agents
- ~2-3 weeks of focused implementation

---

### Concept E: "The Workshop" -- Spatial Project Canvas

*Combines: Spatial Interface + Single Surface + Agent-as-Character + Rich Embeds*

For project-focused work (EoBQ, Kindred, Ulrich Energy), a tldraw-based infinite canvas where project elements are spatial objects.

**Canvas elements:**
- **Agent cards**: Positioned spatially, draggable, showing what they're working on for this project
- **Task cards**: Kanban-style but free-form positioned. Drag to rearrange. Connect tasks to agents.
- **Asset previews**: Images, code files, documents -- dropped onto the canvas as thumbnails
- **Notes**: Free-text sticky notes for planning
- **Connections**: Draw lines between elements to show relationships

**Agent integration:**
- Ask an agent a question by dragging a message to its card
- Agent responses appear as new cards near the agent
- Creative agent outputs (images) appear as visual cards you can arrange
- Coding agent outputs (diffs, files) appear as code cards

**Why this is interesting but risky:** It's the most creative concept but also the most complex to implement. tldraw provides the canvas infrastructure, but integrating it with the agent API, real-time data, and persistent state is significant work. The risk is building something impressive but unusable -- a spatial interface that's harder to work with than a simple list.

**Pragmatic recommendation:** Build this as an optional "workshop" view for individual projects, not as the primary interface. If it works well, expand it. If it doesn't, the traditional project pages remain.

**Technical requirements:**
- tldraw SDK integration in Next.js
- Custom shape definitions for agent cards, task cards, asset previews
- Persistence layer (save canvas state per project)
- Agent API integration (send messages to agents from canvas)
- ~6-8 weeks for minimum viable version

---

## 13. Implementation Roadmap

### Priority Matrix

| Concept | Impact | Effort | Viability | Priority |
|---------|--------|--------|-----------|----------|
| Command palette (Cmd+K) | Very High | Low | Very High | **P0 -- Do first** |
| Agent portrait bar | High | Low-Medium | Very High | **P1** |
| Glanceable widget system | High | Medium | Very High | **P1** |
| Activity stream unification | High | Medium | Very High | **P1** |
| Calm/ambient visual treatment | High | Low | Very High | **P1** |
| Living breathing CSS | Medium-High | Low | High | **P1** |
| The Furnace (home surface) | Very High | Medium | High | **P2** |
| Generative UI (chat components) | Very High | Medium-High | High | **P2** |
| The Lens (intent mode) | Very High | Medium | High | **P2** |
| Agent identity system | Medium | Low | Very High | **P2** |
| Feedback surfaces | Medium | Medium | High | **P3** |
| Smart Stack contextual surfacing | Medium | Medium | Medium-High | **P3** |
| Voice + visual multimodal | Medium | High | Medium | **P4** |
| System map (spatial overview) | Medium | High | Medium | **P4** |
| Project canvas (tldraw) | Medium | Very High | Medium | **P5** |

### Phase 1: Foundation (1-2 weekends)

1. **Command palette** (Cmd+K): shadcn/ui `CommandDialog` + fuzzy search over agents, services, projects, actions. Keyboard shortcut registration. History of recent commands.

2. **Agent portrait bar**: Persistent bottom bar with 8 agent circles. Color-coded. State-driven CSS (idle/active/escalating). Click opens detail panel.

3. **Calm visual foundation**: CSS custom properties for system state. `--system-warmth` driven by overall activity. `--breath-speed` driven by load. Applied to background, borders, and accent elements.

### Phase 2: The Living Home (2-3 weekends)

4. **Glanceable widget components**: Small/medium/large widget sizes. GPU status widget. Agent summary widget. Active tasks widget. Media widget. Home widget.

5. **Unified activity stream**: Merge activity + tasks + chat into one reverse-chronological view. Agent color coding. Type filtering. Expandable detail.

6. **The Furnace home surface**: Integrate agent constellation, contextual widgets, and ambient visual treatment into the home page.

### Phase 3: Intelligence (2-4 weekends)

7. **Generative UI**: Vercel AI SDK integration for chat responses that render React components. Start with 3-4 component types (GPU chart, media gallery, task status).

8. **Intent/lens mode**: Command palette triggers lens changes. URL query params for bookmarkability. Smooth layout transitions.

9. **Feedback surfaces**: Inline micro-feedback on agent outputs. Behavioral tracking for preference inference. Immediate feedback demonstration (level 5).

### Phase 4: Advanced (ongoing)

10. **Smart Stack**: ML-lite priority algorithm for widget surfacing based on time, behavior, and escalation state.

11. **Voice + visual integration**: WebSocket bridge from HA voice pipeline to dashboard for multimodal responses.

12. **System map**: Simplified spatial overview (not full ZUI) showing nodes, agents, and connections.

### Technical Dependencies

| Dependency | Required For | Status |
|------------|-------------|--------|
| Motion library (`motion` npm package) | Ambient animation, layout transitions | Not installed, trivial to add |
| Vercel AI SDK (`ai` npm package) | Generative UI | Not installed, needs evaluation |
| WebSocket infrastructure | Real-time updates, voice integration | Not implemented, needs SSE or WS layer |
| Agent API streaming | Generative UI responses | Needs streaming endpoint on agent framework |
| tldraw SDK | Project canvas | Not installed, Phase 4+ |

---

## 14. Sources

### Protocols and Frameworks
- [Vercel AI SDK Documentation](https://ai-sdk.dev/docs/introduction)
- [Vercel AI SDK 3.0 Generative UI Announcement](https://vercel.com/blog/ai-sdk-3-generative-ui)
- [AI SDK RSC: Streaming React Components](https://ai-sdk.dev/docs/ai-sdk-rsc/streaming-react-components)
- [AI SDK RSC: createStreamableUI](https://ai-sdk.dev/docs/reference/ai-sdk-rsc/create-streamable-ui)
- [Google A2UI Announcement](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/)
- [A2UI Specification](https://a2ui.org/)
- [A2UI GitHub](https://github.com/google/A2UI)
- [AG-UI Protocol (CopilotKit)](https://www.copilotkit.ai/ag-ui)
- [CopilotKit GitHub](https://github.com/CopilotKit/CopilotKit)
- [AG-UI GitHub](https://github.com/ag-ui-protocol/ag-ui)

### Calm Technology and Ambient Computing
- [Amber Case: Principles of Calm Technology](https://www.caseorganic.com/post/principles-of-calm-technology)
- [calmtech.com](https://calmtech.com/)
- [Calm Technology - Wikipedia](https://en.wikipedia.org/wiki/Calm_technology)
- [Weiser & Brown: "Designing Calm Technology" (1995)](https://www.semanticscholar.org/paper/Designing-Calm-Technology-Weiser/fdc2e87fcb4575bdf5154840ebd19c2dd490165c)
- [Case: Calm Technology (O'Reilly, 2015)](https://www.oreilly.com/library/view/calm-technology/9781491925874/)

### Spatial and Zoomable Interfaces
- [Bederson: Pad++ Paper](https://www.cs.umd.edu/~bederson/images/pubs_pdfs/p23-bederson.pdf)
- [ZUI Overview (ScienceDirect)](https://www.sciencedirect.com/topics/computer-science/zoomable-user-interface)
- [Navigation patterns in ZUIs (UMD)](http://www.cs.umd.edu/hcil/trs/2001-11/2001-11.html)
- [tldraw SDK](https://tldraw.dev/)
- [tldraw GitHub](https://github.com/tldraw/tldraw)
- [Apple visionOS Design HIG](https://developer.apple.com/design/human-interface-guidelines/designing-for-visionos)

### Agent Anthropomorphism
- [Anthropomorphism in Chatbot Avatars (Frontiers, 2025)](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1531976/full)
- [Benefits and Dangers of Anthropomorphic Agents (PNAS, 2025)](https://www.pnas.org/doi/10.1073/pnas.2415898122)
- [AI Anthropomorphism - Wikipedia](https://en.wikipedia.org/wiki/AI_anthropomorphism)

### Intention-Based Interfaces
- [Invisible by Design: Context-Aware Interfaces (vonThenen, 2025)](https://davidvonthenen.com/2025/09/10/invisible-by-design-context-aware-interfaces-that-assemble-themselves/)
- [Command Palette Interfaces (Fountn)](https://fountn.design/resource/command-palette-interfaces/)
- [Command Palette Activation (Multi)](https://multi.app/blog/nailing-the-activation-behavior-of-a-spotlight-raycast-like-command-palette)

### Activity Streams and Timelines
- [Activity Stream Pattern (ui-patterns.com)](https://ui-patterns.com/patterns/ActivityStream)
- [Chronological Activity Feed Design (Aubergine)](https://www.aubergine.co/insights/a-guide-to-designing-chronological-activity-feeds)
- [Activity Feed Design (GetStream)](https://getstream.io/blog/activity-feed-design/)
- [Event Sourcing (Martin Fowler)](https://martinfowler.com/eaaDev/EventSourcing.html)

### Glanceable Design
- [Apple HIG: Widgets](https://developer.apple.com/design/human-interface-guidelines/widgets/)
- [Design Great Widgets (WWDC20)](https://developer.apple.com/videos/play/wwdc2020/10103/)
- [Smart Stack Widgets (WWDC23)](https://developer.apple.com/videos/play/wwdc2023/10309/)

### Multimodal Interfaces
- [Voice UX Design & Multimodal Interfaces (Payoda)](https://www.payoda.com/voice-ux-design-multimodal-voice-interfaces-explained/)
- [Designing Multimodal AI Interfaces (FuseLab)](https://fuselabcreative.com/designing-multimodal-ai-interfaces-interactive/)
- [VUI Design Principles 2026 (ParallelHQ)](https://www.parallelhq.com/blog/voice-user-interface-vui-design-principles)

### Feedback and Control
- [Feedback + Control (Google PAIR)](https://pair.withgoogle.com/chapter/feedback-controls/)
- [Beyond Explicit and Implicit Feedback (CHI 2025)](https://dl.acm.org/doi/full/10.1145/3706598.3713241)
- [Fine-Grained Feedback for T2I (arXiv)](https://arxiv.org/html/2406.16807)
- [Feedback by Design (arXiv, 2025)](https://arxiv.org/html/2602.01405v1)

### Animation and Motion
- [Motion.dev (formerly Framer Motion)](https://motion.dev)
- [React Animation (Motion)](https://motion.dev/docs/react-animation)
- [Motion UI Trends 2026](https://lomatechnology.com/blog/motion-ui-trends-2026/2911)

### Chat and Rich Messaging
- [Slack Block Kit](https://docs.slack.dev/block-kit/)
- [Slack Interactive Messages](https://docs.slack.dev/messaging/creating-interactive-messages/)
- [ChatGPT Canvas vs Claude Artifacts](https://xsoneconsultants.com/blog/chatgpt-canvas-vs-claude-artifacts/)

### Game UI
- [Game UI Database](https://www.gameuidatabase.com/)
- [Game HUD Design (Polydin)](https://polydin.com/game-hud-design/)

### Music Production (Complexity Management Reference)
- [Ableton Live vs Logic Pro (LANDR)](https://blog.landr.com/logic-vs-ableton/)
- [Ableton Live 12 Enhancements](https://mixingmonster.com/ableton-live/)

### General AI Interface Design
- [Google Generative UI Research](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
- [Chat UI Design Trends 2025 (MultitaskAI)](https://multitaskai.com/blog/chat-ui-design/)
- [Conversational AI UI Comparison 2025 (IntuitionLabs)](https://intuitionlabs.ai/articles/conversational-ai-ui-comparison-2025)
- [Context-Aware Interfaces (DEV Community)](https://dev.to/pixel_mosaic/top-uiux-design-trends-for-2026-ai-first-context-aware-interfaces-spatial-experiences-166j)

---

## Appendix: Cross-Domain Inspiration

### From Music Production (Ableton Live)

Ableton Live's **Session View vs. Arrangement View** duality is directly applicable:
- **Session View**: Non-linear, loop-based, experimental. Launch clips in any order. Think of this as the "agent playground" -- trigger agents, see results, iterate.
- **Arrangement View**: Linear, timeline-based, structured. Build a composition from start to finish. Think of this as the "project view" -- tasks ordered, dependencies tracked, progress linear.

The critical insight: the same underlying data (audio clips / agent tasks) can be viewed in two fundamentally different ways depending on whether you're exploring or executing. Athanor could offer both: a session-style view for interactive exploration and an arrangement-style view for structured project work.

Ableton's **Info View** -- hover over any UI element and get an explanation in a persistent help panel -- is a pattern worth stealing for a complex dashboard. Context-sensitive help without modal dialogs.

### From Film (Editing Timelines)

Video editing software (DaVinci Resolve, Premiere Pro) manages extreme complexity through:
- **Multi-track timelines**: Multiple parallel lanes of activity, each independently zoomable
- **Playhead as time cursor**: A single vertical line that sweeps across all tracks simultaneously
- **Markers**: User-placed annotations on the timeline for quick navigation
- **In/Out points**: Defining focus regions within the timeline

Applied to Athanor's activity stream: multiple "tracks" (one per agent), a time cursor for reviewing history, user-placed markers ("I approved this point"), and the ability to define time windows for focused review.

### From Architecture (Wayfinding)

Kevin Lynch's "The Image of the City" (1960) identifies five elements of navigable spaces: paths, edges, districts, nodes, and landmarks. Applied to dashboard navigation:

- **Paths**: The navigation patterns users follow (command palette, breadcrumbs, agent portrait bar)
- **Edges**: Boundaries between domains (AI / media / home / system)
- **Districts**: Groups of related functionality (the "creative district" = ComfyUI + Creative Agent + GPU status)
- **Nodes**: Decision points (the home surface, the command palette)
- **Landmarks**: Distinctive, memorable elements (the agent constellation, the furnace glow)

A well-designed dashboard should be navigable without a manual, just as a well-designed city is walkable without a map.

### From Games (HUD Design)

The best game HUDs follow a principle called **"progressive disclosure through immersion"**:
- **Minimal HUD (normal play)**: Only essential information (health, ammo, minimap)
- **Expanded HUD (on request)**: Full stats, inventory, quest log when the player pauses or opens a menu
- **Contextual HUD (triggered by events)**: Damage indicators, loot notifications, quest updates appear momentarily and fade

This maps exactly to calm technology principles applied to a dashboard: minimal by default, expanded on request, contextual when events demand attention.

---

*Research complete. The recommended approach is to start with Concept A (The Furnace) as the home surface, Concept D (The Crew) as the persistent agent presence, and the command palette as the primary navigation mechanism. These three together create a novel interface that feels alive, is instantly navigable, and honors the athanor metaphor. Generative UI (Concept B) and intent mode (Concept C) are the high-impact follow-ups.*
