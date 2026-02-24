# Kindred — Concept Document

*Passion-based social matching application.*

**Status:** Concept / research phase. No code, no ADR, no implementation decisions.

---

## Core Concept

People are matched on shared passions and interests rather than conventional dating/social metrics. The hypothesis: deep shared interests create more meaningful connections than demographic similarity.

---

## Passion Taxonomy

Passions aren't binary (has/doesn't have) — they have depth, recency, and specificity.

**Hierarchical categories:** Music → Jazz → Bebop → Thelonious Monk. Two people who share specificity at the Monk level are a stronger match than two people who both "like music."

**Decay:** Passions decay over time without engagement. Someone passionate about chess 5 years ago who hasn't played since isn't the same as an active tournament player.

**Intensity signals:**
- Self-rated (unreliable)
- Behavioral (time spent, content consumed, groups joined)
- Social proof (what others say)

---

## Matching Algorithm (Conceptual)

- Vector similarity on passion embeddings is the baseline — but raw cosine similarity overweights breadth (lots of shallow matches) vs depth (fewer but meaningful matches)
- **Weighted approach:** depth of shared passion > breadth of overlapping interests
- Geographic proximity as a soft filter, not a hard filter — a perfect passion match 50 miles away is worth surfacing
- **Anti-pattern detection:** filter people who list passions for matching purposes but don't actually engage with them (the "I love hiking" person whose activity data shows zero hikes)

### Cold Start Problem

New users have no behavioral data. Solution: onboarding flow that maps passion depth through interactive questions, not checkboxes.

"Tell me about something you could talk about for hours" → NLP extracts passion signals from free-text responses.

---

## Athanor Integration

- Recommendation engine runs on Athanor's inference stack
- Embedding generation for passion vectors uses the same embedding model as the Knowledge Agent (Qwen3-Embedding-0.6B on Node 1:8001)
- Database likely PostgreSQL with pgvector extension for similarity search
- Content moderation routes through cloud models (nothing inherently needs uncensored models)

---

## When to Build

Phase 5+ project. After Athanor's core infrastructure is stable. Use Deep Trilogy's `/deep-project` to decompose requirements when the time comes.
