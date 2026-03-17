---
description: Research a topic for Athanor. Search current information, document findings with citations, flag contradictions with existing decisions.
allowed-tools: WebFetch, WebSearch, Agent, Bash(curl:*), Bash(cat:*), Read, Write, Edit, Grep, Glob
---

Research the topic: $ARGUMENTS

1. Break down what needs to be researched
2. Search for current information — prioritize official docs, benchmarks, GitHub repos, real user experiences
3. Use WebSearch and WebFetch for current information
4. Check docs/research/ for prior notes on this topic
5. Check docs/decisions/ for any existing ADRs this might affect
6. Document findings in docs/research/YYYY-MM-DD-{topic-slug}.md with:
   - Source URLs for every claim
   - Key findings
   - Open questions
   - Recommendation (if research is sufficient)
7. Flag contradictions with existing content
8. Apply the One-Person Scale filter: if a technology requires enterprise ops knowledge, flag it

Do not make architecture decisions in research notes. Research informs decisions; it doesn't make them.
