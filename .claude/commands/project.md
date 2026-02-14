---
description: Switch context to a specific project. Reads that project's documentation and sets up the working context.
allowed-tools: Read, Bash(cat:*), Bash(ls:*), Bash(find:*), Bash(mkdir:*), Grep, Glob, LS, Write
---

Load project context for: $ARGUMENTS

1. Check if projects/{name}/ exists. If not, offer to create it.
2. Check if docs/projects/{name}/ exists. If not, offer to create it.
3. Read all markdown files in docs/projects/{name}/
4. List files in projects/{name}/
5. Summarize:
   - What this project is
   - Current state
   - What was last worked on
   - What's next

If creating a new project:
1. Create projects/{name}/
2. Create docs/projects/{name}/
3. Create docs/projects/{name}/README.md with project description
4. Ask Shaun for initial context about the project
