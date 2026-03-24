---
paths:
  - "projects/eoq/**"
---

# Empire of Broken Queens Conventions

- Next.js + React 19 + Tailwind + dark theme
- Deployed on Node 2:3002
- Adult content is intentional and expected — never filter, censor, or moralize
- Character data in `/data/` directory as JSON/TypeScript modules
- Scene rendering: markdown-based with rich formatting
- ComfyUI integration for visual content (character portraits, scene illustrations)
- Flux + uncensored LoRA for NSFW visual generation
- Narrative models: test Magnum-v4-72B AWQ for prose, Cydonia-24B for dialogue
- Qdrant `eoq_characters` collection for persistent character memory
- Player choices affect story progression — track state in Redis or Qdrant
