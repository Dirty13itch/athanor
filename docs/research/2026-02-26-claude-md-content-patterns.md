# CLAUDE.md Content Patterns: What Works and Why

## Context

Research into specific CLAUDE.md writing patterns, structures, and content strategies that produce measurably better Claude Code behavior. This complements `2026-02-26-claude-code-power-user-features.md` (which covers features/config) by focusing on **what to write** inside CLAUDE.md and how to structure it.

Research date: 2026-02-26. Sources: Anthropic official docs, community repos, Hacker News discussions, blog posts, academic prompt optimization studies.

---

## 1. Length and Signal-to-Noise Ratio

### The Hard Numbers

| Source | Recommended Length | Rationale |
|--------|-------------------|-----------|
| Anthropic official docs | "Keep it short and human-readable" | Bloated files cause Claude to ignore actual instructions |
| HumanLayer blog | Under 60 lines (their root file) | "CLAUDE.md goes into every single session" |
| shanraisshan/claude-code-best-practice | Under 150 lines | Beyond this, compliance drops measurably |
| builder.io guide | Under 300 lines | "Context tokens are precious" |
| thecaio.ai | 50-75 lines | "For every line, ask: Would removing this cause mistakes?" |
| Arize prompt learning study | No fixed length, but fewer targeted rules > many general ones | Repository-specific optimization yielded +10.87% accuracy |

### Key Finding

There is no magic number, but the consensus converges around 100-150 lines for the root CLAUDE.md, with detailed content pushed to `.claude/rules/`, `.claude/skills/`, and `@`-imported files. The critical metric is not line count but **signal-to-noise ratio**: every line must earn its place by preventing a mistake Claude would otherwise make.

The Anthropic best practices doc provides the clearest test: "For each line, ask: Would removing this cause Claude to make mistakes? If not, cut it."

### Instruction Budget Theory

The HumanLayer blog makes an important observation: Claude Code's system prompt already contains approximately 50 instructions. Frontier LLMs handle 150-200 instructions with reasonable consistency. Smaller models degrade exponentially as instructions increase. Your CLAUDE.md instructions compete with the built-in system prompt for adherence capacity.

**Implication**: If your CLAUDE.md adds 100+ instructions on top of the system prompt's 50, you are pushing toward the ceiling where compliance starts degrading. This explains why shorter files perform better -- they stay within the reliable instruction window.

Sources:
- https://code.claude.com/docs/en/best-practices
- https://www.humanlayer.dev/blog/writing-a-good-claude-md
- https://github.com/shanraisshan/claude-code-best-practice
- https://www.builder.io/blog/claude-md-guide
- https://www.thecaio.ai/blog/make-claude-code-follow-instructions

---

## 2. Structure: What Sections to Include

### The WHAT / WHY / HOW Framework

The most-cited structural pattern across sources:

- **WHAT**: Tech stack, project structure, directory map. Give Claude a map of the codebase.
- **WHY**: Purpose of the project and what everything in the repository is for.
- **HOW**: Commands to build/test/lint, verification methods, workflow rules.

### Anthropic's Official Include/Exclude Table

**Include:**
- Bash commands Claude cannot guess
- Code style rules that differ from defaults
- Testing instructions and preferred test runners
- Repository etiquette (branch naming, PR conventions)
- Architectural decisions specific to your project
- Developer environment quirks (required env vars)
- Common gotchas or non-obvious behaviors

**Exclude:**
- Anything Claude can figure out by reading code
- Standard language conventions Claude already knows
- Detailed API documentation (link to docs instead)
- Information that changes frequently
- Long explanations or tutorials
- File-by-file descriptions of the codebase
- Self-evident practices like "write clean code"

### Minimal Effective Structure (60-Line Template)

Based on HumanLayer's real production file and Anthropic's recommendations:

```markdown
# Project Name

One-line description: "Next.js 14 e-commerce with Stripe and Prisma ORM"

## Structure
- `/app`: App Router pages
- `/lib`: Utilities and shared logic
- `/api`: API routes

## Commands
- `npm run dev`: Start dev server (port 3000)
- `npm run test`: Run Jest tests
- `npm run lint`: ESLint check

## Code Style
- TypeScript strict mode, no `any` types
- Named exports, not default exports
- Tailwind for styling, no inline CSS

## Testing
- Write tests first for algorithmic code
- Avoid mocks where integration tests are practical
- Run single test files, not the full suite

## Gotchas
- All routes use `/api/v1` prefix
- JWT tokens expire after 24 hours
- Database migrations must be run manually: `npm run db:migrate`

## Verification
- Run `npm test` after any code changes
- Run `npm run lint` before committing
- Check type errors: `npx tsc --noEmit`
```

### The "Priority Saturation" Problem

claudefa.st identifies a key failure mode: when everything in CLAUDE.md is marked as equally important (high priority), nothing stands out. The solution is to distribute high-priority instructions across targeted contexts:

- **CLAUDE.md**: Universal workflows, project identity, verification commands
- **`.claude/rules/` (with paths)**: Domain-specific rules, loaded only when relevant
- **`.claude/skills/`**: On-demand cross-project patterns

This architecture means API validation rules get emphasis only during API work, not when editing CSS.

Sources:
- https://www.humanlayer.dev/blog/writing-a-good-claude-md
- https://code.claude.com/docs/en/best-practices
- https://claudefa.st/blog/guide/mechanics/rules-directory

---

## 3. Emphasis and Keyword Techniques

### What Works

The Anthropic docs explicitly endorse emphasis markers:

> "You can tune instructions by adding emphasis (e.g., 'IMPORTANT' or 'YOU MUST') to improve adherence."

### Specific Emphasis Patterns (From Community Testing)

| Pattern | Effect | Risk |
|---------|--------|------|
| `IMPORTANT:` prefix | Increases attention to the specific rule | Overuse dilutes impact |
| `CRITICAL:` prefix | Stronger than IMPORTANT, for never-violate rules | Must be truly rare |
| `YOU MUST` | Direct mandate that improves compliance | Sounds aggressive, use sparingly |
| `NEVER` / `DO NOT` | Negative constraints are clearer than positive ones | Can over-constrain |
| `ALL CAPS` for a full rule | Maximum emphasis, highest compliance | If everything is caps, nothing is |
| Bold (`**text**`) | Mild emphasis, good for keywords within rules | Minimal compliance effect |

### The Emphasis Budget

thecaio.ai frames it well: "Using ALL CAPS for every rule is like crying wolf. Claude will start treating emphasized text the same as regular text." Reserve maximum emphasis for 2-3 rules that are genuinely critical.

### Instruction Ordering

thecaio.ai also identifies that instruction position matters:

> "Front-load constraints. Place critical requirements at the prompt's beginning, not buried at the end."

Critical rules near the top of CLAUDE.md get higher adherence than those buried in the middle or bottom. This aligns with known positional bias in LLM instruction following (primacy effect).

### "DO NOT" Lists Work Better Than Expected

Multiple sources note that negative constraints ("DO NOT use `require()`") produce clearer boundaries than positive ones ("Use ES modules"). The HumanLayer blog recommends specifying what to avoid explicitly, as it gives Claude sharper decision boundaries.

Sources:
- https://code.claude.com/docs/en/best-practices
- https://www.thecaio.ai/blog/make-claude-code-follow-instructions
- https://www.humanlayer.dev/blog/writing-a-good-claude-md

---

## 4. Progressive Disclosure: The Pointer Pattern

### Core Principle

The single most impactful structural pattern across all sources:

> "Prefer pointers to copies. Don't include code snippets in CLAUDE.md. Instead, include file:line references." -- HumanLayer

### Implementation

Keep CLAUDE.md as a routing document with brief context, then point to detailed files:

```markdown
## Detailed References
- Architecture: @docs/ARCHITECTURE.md
- API conventions: @docs/api-patterns.md
- Deploy process: @docs/deploy.md
- Git workflow: @docs/git-instructions.md
```

Claude loads these on demand when relevant, rather than consuming context tokens on every session.

### `@import` Syntax

The `@path/to/file` syntax in CLAUDE.md tells Claude to read the referenced file when needed:

```markdown
See @README.md for project overview and @package.json for available npm commands.

# Additional Instructions
- Git workflow: @docs/git-instructions.md
- Personal overrides: @~/.claude/my-project-instructions.md
```

Max depth: 5 hops. First encounter per project triggers an approval dialog.

### agent_docs/ Pattern

An alternative from HumanLayer: create a dedicated `agent_docs/` directory with structured reference files:
- `building_the_project.md`
- `running_tests.md`
- `code_conventions.md`
- `service_architecture.md`

Reference these from CLAUDE.md with brief descriptions. Claude decides which are relevant to the current task and reads only those.

Sources:
- https://www.humanlayer.dev/blog/writing-a-good-claude-md
- https://code.claude.com/docs/en/memory

---

## 5. Verification Instructions: The Highest-Leverage Content

### The Anthropic View

The official best practices doc calls this out as the single most important thing:

> "Include tests, screenshots, or expected outputs so Claude can check itself. This is the single highest-leverage thing you can do."

### What This Looks Like in Practice

```markdown
## Verification
- After code changes: `npm test`
- After style changes: `npm run lint`
- After type changes: `npx tsc --noEmit`
- After API changes: `curl localhost:3000/api/health`
- After DB changes: `npm run db:migrate && npm test`
```

This transforms Claude from a code generator into a self-correcting system. Without verification commands, Claude produces plausible-looking code that may not actually work. With them, Claude runs the verification, catches its own mistakes, and iterates.

### Test-Driven Approach

Multiple HN commenters and blog authors converge on this: include TDD instructions in CLAUDE.md for algorithmic work:

```markdown
## Workflow for New Features
1. Write failing tests first
2. Implement until tests pass
3. Run full lint + type check
4. Commit only when all checks pass
```

Sources:
- https://code.claude.com/docs/en/best-practices
- https://news.ycombinator.com/item?id=44362244

---

## 6. Compaction Survival Instructions

### The Problem

When context runs low, Claude automatically compacts the conversation. Your CLAUDE.md survives compaction (it is re-injected), but any nuanced understanding built during the session may be lost.

### The Pattern

Add explicit compaction instructions to CLAUDE.md:

```markdown
## After Compaction
1. Read the plan file if one exists
2. `git log --oneline -5` + `git diff --stat` for what just happened
3. Continue where you left off -- do not re-orient or restart
```

This gives Claude a recovery procedure that fires automatically after compaction restores CLAUDE.md to context.

### Custom Compaction Focus

You can also tell Claude what to prioritize during compaction:

```markdown
## When Compacting
Always preserve: the full list of modified files, any test commands used,
the current implementation plan, and all error messages encountered.
```

### PreCompact Hook Pattern

Beyond CLAUDE.md instructions, the PreCompact hook (covered in the power-user features doc) can create handover documents that survive compaction:

```json
{
  "hooks": {
    "PreCompact": [{
      "matcher": "auto",
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/pre-compact-handover.py"
      }]
    }]
  }
}
```

The hook spawns a fresh Claude instance to summarize the current session into a `HANDOVER-YYYY-MM-DD.md` file before compaction occurs.

Sources:
- https://yuanchang.org/en/posts/claude-code-auto-memory-and-hooks/
- https://code.claude.com/docs/en/best-practices

---

## 7. Anti-Patterns to Avoid

### Documented Anti-Patterns (From Multiple Sources)

**1. The Kitchen Sink CLAUDE.md**

Symptoms: 400+ lines, multiple unrelated concerns, API rules next to CSS rules next to deployment procedures. Result: Claude ignores most of it.

Fix: Extract domain-specific content to `.claude/rules/` with path scoping.

**2. Linting by Instruction**

HumanLayer: "Never send an LLM to do a linter's job." If you want consistent formatting, use prettier/eslint/ruff and enforce via hooks, not CLAUDE.md instructions.

Fix: PostToolUse hook that runs lint after every file edit.

**3. Auto-Generated Without Review**

Running `/init` and never editing the output. The generated file is a starting point, not a finished product.

Fix: "Spend some time thinking very carefully about every single line."

**4. Stale Instructions**

Rules that made sense months ago but no longer apply. Patterns that have changed. Technologies that were replaced.

Fix: Review CLAUDE.md monthly. Delete anything that no longer prevents mistakes.

**5. Code Style Novels**

Multi-paragraph explanations of why you prefer a certain pattern. Claude does not need the rationale -- it needs the rule.

Before: "We use named exports because they make refactoring easier and provide better tree-shaking. Default exports can cause issues with re-exports and make it harder to trace usage across the codebase."

After: "Use named exports, not default exports."

**6. Documenting What Claude Already Knows**

Instructions like "use descriptive variable names" or "add comments to complex code" or "follow PEP 8." Claude already does these things.

Fix: Only document deviations from standard practice.

**7. Duplicating README/docs Content**

Copying project descriptions, setup guides, or architecture docs into CLAUDE.md.

Fix: Use `@README.md` to reference them instead.

Sources:
- https://www.humanlayer.dev/blog/writing-a-good-claude-md
- https://code.claude.com/docs/en/best-practices
- https://github.com/shanraisshan/claude-code-best-practice

---

## 8. Real-World Examples from Notable Projects

### Anthropic's Internal Practice

From "How Anthropic Teams Use Claude Code" (official PDF):

- "The better you document your workflows, tools, and expectations in Claude.md files, the better Claude Code performs."
- Data Infrastructure team: documented existing pipeline patterns so Claude could replicate them for new pipelines.
- Security team: used 50% of all custom slash commands in the monorepo -- slash commands (skills) rather than CLAUDE.md instructions.
- RL Engineering team: "Give Claude a quick prompt and let it attempt the full implementation first. If it works (about one-third of the time), you've saved significant time."

Key takeaway: Anthropic's own teams lean heavily on skills and slash commands for specific workflows, keeping CLAUDE.md for universal context.

### HumanLayer Production File (Under 60 Lines)

Structure:
1. One-line project description
2. Tech stack list
3. Directory structure (6-8 key dirs)
4. Build/test/lint commands (exact syntax)
5. 3-4 code style rules that deviate from defaults
6. Links to detailed docs in `agent_docs/`

No architectural decisions, no workflow descriptions, no rationale paragraphs.

### ArthurClune/claude-md-examples

Provides templates for Python, Hugo, and Terraform projects. Key pattern: each template is technology-specific and focused:

- Python template: virtualenv activation, pytest command, type checking, import ordering
- Terraform template: `terraform fmt`, `terraform validate`, plan-before-apply workflow
- Hugo template: build command, content directory structure, shortcode conventions

### Chris Dzombak's Approach (dzombak.com)

Uses two files:
1. **Project CLAUDE.md**: Structure, build processes, lint commands
2. **`~/.claude/CLAUDE.md`**: Personal global guidelines covering development philosophy, process stages, technical standards

Personal guidelines include a stopping rule: "maximum three attempts per problem before reassessing the entire approach."

### Claude Code Creator's Approach (HN Discussion)

From the HN thread about the Claude Code creator's setup:
- Skills that invoke Python scripts to guide agents through workflows
- Multi-phase approach: planning (1+ hours) then execution
- "Do not allow the LLM to make any implicit decisions, but instead confirm with the user"
- Code written to be "easy to understand for LLMs" -- Claude-friendly code structure

Sources:
- https://codingscape.com/blog/how-anthropic-engineering-teams-use-claude-code-every-day
- https://www.humanlayer.dev/blog/writing-a-good-claude-md
- https://github.com/ArthurClune/claude-md-examples
- https://www.dzombak.com/blog/2025/08/getting-good-results-from-claude-code/
- https://news.ycombinator.com/item?id=46470017

---

## 9. Instruction Retention Across Conversation Length

### The Decay Problem

From dev.to research, compliance decays predictably across conversation turns:

| Turn Range | Compliance Rate |
|------------|----------------|
| Messages 1-2 | 95%+ |
| Messages 3-5 | 60-80% |
| Messages 6-10 | 20-60% |

This is not a CLAUDE.md problem per se -- it is a context window filling problem. As conversation grows, CLAUDE.md instructions compete with accumulated conversation history for attention.

### Mitigation Strategies

1. **`/clear` between unrelated tasks**: The official recommendation. Prevents irrelevant context from diluting instructions.

2. **Restate constraints in prompts**: For critical rules, repeat them in the prompt itself: "Remember to use named exports. Implement the feature."

3. **Hooks over instructions**: For rules that must be enforced 100% of the time, convert them to hooks. A PostToolUse hook that runs the linter will enforce formatting every time, regardless of context window state.

4. **Subagents for investigation**: Delegate codebase exploration to subagents so the main conversation context stays clean for implementation.

5. **Shorter sessions**: The "two corrections" rule from Anthropic: "If you've corrected Claude more than twice on the same issue in one session, the context is cluttered with failed approaches. Run `/clear` and start fresh."

Sources:
- https://dev.to/siddhantkcode/an-easy-way-to-stop-claude-code-from-forgetting-the-rules-h36
- https://code.claude.com/docs/en/best-practices

---

## 10. The Prompt Optimization Feedback Loop

### Arize Study: Measurable CLAUDE.md Improvement

The Arize AI study applied systematic prompt optimization to CLAUDE.md and measured results:

- **Cross-repository generalization**: +5.19% accuracy improvement
- **Repository-specific optimization**: +10.87% accuracy boost

Methodology:
1. Split test cases into train/test
2. Run Claude Code on training examples with baseline CLAUDE.md
3. Evaluate with unit tests (binary pass/fail)
4. Use an LLM to generate feedback explaining why solutions succeeded or failed
5. Use a meta-prompt to generate optimized CLAUDE.md rules from the feedback
6. Validate on test set
7. Iterate until performance plateaus

Key insight: "LLM evals provide richer learning signals than scalar rewards" -- the feedback identifies specific failure modes (misunderstood APIs, missing edge cases, incorrect assumptions) which enables targeted rule creation rather than generic advice.

### Practical Application

You do not need the full academic pipeline. The core loop is:

1. Observe a repeated mistake Claude makes
2. Add a targeted rule to CLAUDE.md addressing that specific mistake
3. Test in subsequent sessions
4. If compliance improves, keep the rule. If not, rephrase or escalate to a hook.
5. Periodically remove rules for mistakes Claude no longer makes

This is the "treat CLAUDE.md like code" principle in action.

Sources:
- https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/

---

## 11. MEMORY.md Optimization Patterns

### The 200-Line Constraint

Only the first 200 lines of MEMORY.md are loaded into the system prompt at session start. Content beyond line 200 exists on disk but is not automatically loaded.

### Effective MEMORY.md Structure

```
~/.claude/projects/<project>/memory/
  MEMORY.md          # Index (under 200 lines)
  debugging.md       # Detailed patterns
  api-conventions.md # Design decisions
  infrastructure.md  # Deployment notes
```

MEMORY.md serves as a concise index with pointers to topic files. Topic files are read on demand when relevant.

### What Auto-Memory Captures Well

- Project build/test conventions
- Solutions to problematic issues and root causes
- Key files, module relationships, critical abstractions
- User communication patterns and tool preferences

### What Auto-Memory Gets Wrong

Auto-memory sometimes records incorrect patterns or stale information. Use `/memory` periodically to review and correct entries. Stale memory is worse than no memory -- it causes Claude to confidently apply outdated patterns.

### Direct Memory Commands

- "Remember that we use pnpm, not npm"
- "Save to memory that the API tests require a local Redis instance"
- "Forget the pattern about using default exports"

3-5 memorized instructions can transform Claude's default behavior for a project.

Sources:
- https://code.claude.com/docs/en/memory
- https://yuanchang.org/en/posts/claude-code-auto-memory-and-hooks/
- https://institute.sfeir.com/en/claude-code/claude-code-memory-system-claude-md/tips/

---

## 12. Extended Thinking Keywords (Deprecated but Informative)

### Historical Pattern

Claude Code previously supported trigger keywords in prompts:

| Keyword | Thinking Budget |
|---------|----------------|
| "think" | 4,000 tokens |
| "think harder" / "think deeply" | 10,000 tokens (megathink) |
| "ultrathink" | 31,999 tokens (maximum) |

### Current State (Feb 2026)

Extended thinking is now enabled by default with maximum budget. The `/effort` command provides granular control (low/medium/high/max). The magic keywords are deprecated.

### Relevance to CLAUDE.md

You can set `alwaysThinkingEnabled: true` in settings.json or use `CLAUDE_CODE_EFFORT_LEVEL` env var. Including thinking instructions in CLAUDE.md is no longer necessary or useful.

Sources:
- https://claudelog.com/faqs/what-is-ultrathink/
- https://decodeclaude.com/ultrathink-deprecated/

---

## Athanor Assessment

### Current Athanor CLAUDE.md: 130 Lines

Our file is well within the recommended range. Structure analysis:

| Section | Lines | Assessment |
|---------|-------|------------|
| Role definition | ~20 | Strong -- clear identity, decision framework, escalation rules |
| How We Work | ~20 | Strong -- principles are actionable, anti-patterns defined |
| Compaction recovery | ~5 | Good -- explicit recovery procedure |
| Build/Operational modes | ~5 | Good -- clear triggers and workflows |
| Project structure | ~15 | Moderate -- mostly pointers (good) but some inline detail |
| Hardware table | ~10 | Could be moved to skill/rule -- not needed every session |
| Current State | ~8 | Heavy -- dense paragraph with numbers that change frequently |
| Key Gotchas | ~8 | Strong -- exactly the kind of content that belongs here |
| Blockers | ~8 | Moderate -- useful for context but changes frequently |
| Never Do | ~8 | Strong -- negative constraints work well |

### What Athanor Does Well

1. **Role-first structure**: Opening with identity and decision framework aligns with the "WHY before WHAT" pattern.
2. **Anti-patterns section**: Explicit "Don't say 'Let me check...' then check -- just check" is exactly the kind of behavioral rule that CLAUDE.md excels at.
3. **Gotchas section**: Hardware-specific gotchas (Blackwell sm_120, VAULT SSH, NFS stale handles) are precisely what should be in CLAUDE.md -- things Claude cannot infer from code.
4. **Never Do section**: Clean negative constraints at the end.
5. **Progressive disclosure**: "See `.claude/rules/` for domain-specific gotchas" pushes detail to where it belongs.
6. **Compaction recovery**: Explicit procedure that fires after context reset.

### Opportunities for Improvement

1. **Current State section**: The dense paragraph with exact numbers (2,304 items, 3,095 nodes, etc.) changes frequently and creates maintenance burden. Consider moving to a skill or `@docs/SYSTEM-SPEC.md` reference. Keep only the structural facts (how many agents, which nodes run what).

2. **Hardware table**: Not needed in every session. When working on EoBQ or dashboard code, the EPYC specs are noise. Move to a path-scoped rule or skill that loads when working on `ansible/` or hardware docs.

3. **Blockers table**: Changes frequently. Could be moved to a separate file (`@BLOCKERS.md`) that is referenced but not inlined.

4. **Missing verification commands**: The CLAUDE.md lacks explicit "how to verify your work" instructions. This is the highest-leverage omission per Anthropic's best practices. Add commands for running tests, checking ansible syntax, verifying docker builds.

5. **Missing @imports**: No `@`-references to external docs. Adding `@docs/VISION.md` and `@docs/SYSTEM-SPEC.md` as pointers would let Claude pull them on demand without inlining content.

6. **Emphasis usage**: Only one emphasis marker ("Decide, don't defer" in bold). The "Never Do" section and key gotchas could benefit from selective IMPORTANT/CRITICAL prefixes on the most-violated rules.

---

## Summary: The 10 Most Impactful Patterns

1. **Test the removal**: For every line, ask "Would removing this cause Claude to make mistakes?" If not, cut it.

2. **Verification first**: Include exact commands Claude can run to verify its own work. This is the single highest-leverage content.

3. **Pointers over copies**: Reference files with `@path` instead of inlining content. Keep CLAUDE.md as a routing document.

4. **Path-scoped rules for domains**: Move domain-specific rules to `.claude/rules/` with `paths:` frontmatter. API rules load only during API work.

5. **Hooks for enforcement**: If a rule must be followed 100% of the time, convert it from a CLAUDE.md instruction to a hook. Instructions are advisory; hooks are deterministic.

6. **Front-load critical rules**: Position the most important rules at the top of CLAUDE.md. Primacy effect improves compliance.

7. **Reserve emphasis for 2-3 rules**: Use IMPORTANT/CRITICAL/NEVER sparingly. Overuse dilutes impact.

8. **Negative constraints are sharper**: "DO NOT use require()" is clearer than "Use ES modules."

9. **Compaction recovery procedure**: Include explicit instructions for what Claude should do after context compaction.

10. **Monthly pruning**: Review CLAUDE.md regularly. Delete rules for mistakes Claude no longer makes. Update rules that have drifted from current practice.

---

## Sources

- [Anthropic Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Anthropic: Using CLAUDE.md Files](https://claude.com/blog/using-claude-md-files)
- [Anthropic: How Anthropic Teams Use Claude Code](https://codingscape.com/blog/how-anthropic-engineering-teams-use-claude-code-every-day)
- [HumanLayer: Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [builder.io: How to Write a Good CLAUDE.md File](https://www.builder.io/blog/claude-md-guide)
- [Arize: CLAUDE.md Best Practices from Prompt Learning](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)
- [claudefa.st: Rules Directory Guide](https://claudefa.st/blog/guide/mechanics/rules-directory)
- [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
- [ArthurClune/claude-md-examples](https://github.com/ArthurClune/claude-md-examples)
- [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips)
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)
- [thecaio.ai: Make Claude Code Follow Instructions](https://www.thecaio.ai/blog/make-claude-code-follow-instructions)
- [dev.to: Stop Claude Code From Forgetting Rules](https://dev.to/siddhantkcode/an-easy-way-to-stop-claude-code-from-forgetting-the-rules-h36)
- [dzombak.com: Getting Good Results from Claude Code](https://www.dzombak.com/blog/2025/08/getting-good-results-from-claude-code/)
- [yuanchang.org: Claude Code Auto Memory and Hooks](https://yuanchang.org/en/posts/claude-code-auto-memory-and-hooks/)
- [SFEIR: Memory System Tips](https://institute.sfeir.com/en/claude-code/claude-code-memory-system-claude-md/tips/)
- [HN: Ask HN How Do You Use Claude Code Effectively](https://news.ycombinator.com/item?id=44362244)
- [HN: The Creator of Claude Code's Setup](https://news.ycombinator.com/item?id=46470017)
- [claudelog.com: What is UltraThink](https://claudelog.com/faqs/what-is-ultrathink/)
