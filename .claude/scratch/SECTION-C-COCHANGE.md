# Section C: Co-change Clusters & Temporal Coupling Analysis

*Generated: 2026-03-14 | HEAD: b1d1ded | Branch: main | Last 300 commits analyzed*

---

## 1. Co-change Cluster Detection [VERIFIED]

### Top 20 File Pairs That Change Together

| Co-changes | File A | File B |
|------------|--------|--------|
| 16 | CLAUDE.md | docs/BUILD-MANIFEST.md |
| 11 | docs/BUILD-MANIFEST.md | server.py |
| 9 | scheduler.py | server.py |
| 9 | MEMORY.md | docs/BUILD-MANIFEST.md |
| 8 | STATUS.md | docs/BUILD-MANIFEST.md |
| 8 | docs/BUILD-MANIFEST.md | docs/SERVICES.md |
| 8 | CLAUDE.md | MEMORY.md |
| 7 | context.py | server.py |
| 7 | CLAUDE.md | server.py |
| 7 | CLAUDE.md | docs/SYSTEM-SPEC.md |
| 7 | docs/BUILD-MANIFEST.md | docs/SYSTEM-SPEC.md |
| 7 | CLAUDE.md | docs/SERVICES.md |
| 6 | server.py | tasks.py |
| 5 | vault-litellm defaults | litellm_config template |
| 5 | docs/SERVICES.md | docs/SYSTEM-SPEC.md |
| 4 | server.py | workspace.py |
| 4 | agent-contracts.md | intelligence-layers.md |
| 4 | agents defaults | agents compose template |
| 4 | grafana-alerts tasks | backup-alerts template |
| 4 | core.yml | interface.yml |

*(All paths abbreviated; full paths in raw data. server.py = `projects/agents/src/athanor_agents/server.py`)*

### Interpretation

BUILD-MANIFEST.md is the gravitational center of the codebase -- it co-changes with nearly everything because work tracking updates accompany code changes. The real architectural coupling signal is in the non-meta pairs: **server.py couples with scheduler.py (9x), context.py (7x), tasks.py (6x), and workspace.py (4x)** -- these form the core agent runtime cluster.

---

## 2. Churn Hotspot Analysis [VERIFIED]

### Raw Change Frequency (top 15)

| Changes | File |
|---------|------|
| 66 | docs/BUILD-MANIFEST.md |
| 52 | STATUS.md |
| 52 | server.py |
| 46 | CLAUDE.md |
| 24 | docs/SYSTEM-SPEC.md |
| 20 | MEMORY.md |
| 19 | docs/SERVICES.md |
| 17 | scheduler.py |
| 16 | config.ts (dashboard) |
| 16 | sidebar-nav.tsx |
| 15 | .mcp.json |
| 14 | tasks.py |
| 14 | .claude/settings.json |
| 13 | context.py |
| 12 | more/page.tsx |

### Churn Score (changes x LOC, top 15) [VERIFIED]

Churn score weights change frequency by file size, surfacing files that are both large and volatile -- the highest-risk maintenance targets.

| Churn Score | Changes | LOC | File |
|-------------|---------|-----|------|
| 131,716 | 52 | 2,533 | server.py |
| 75,372 | 66 | 1,142 | docs/BUILD-MANIFEST.md |
| 28,444 | 52 | 547 | STATUS.md |
| 13,032 | 24 | 543 | docs/SYSTEM-SPEC.md |
| 12,240 | 16 | 765 | config.ts (dashboard) |
| 11,577 | 17 | 681 | scheduler.py |
| 11,102 | 14 | 793 | tasks.py |
| 9,009 | 13 | 693 | context.py |
| 7,776 | 9 | 864 | workspace.py |
| 7,263 | 9 | 807 | scripts/index-knowledge.py |
| 5,994 | 9 | 666 | workplanner.py |
| 5,850 | 9 | 650 | globals.css |
| 4,970 | 7 | 710 | self_improvement.py |
| 4,367 | 11 | 397 | test_repo_contracts.py |
| 3,395 | 7 | 485 | escalation.py |

### Key Finding

**server.py** has a churn score of 131,716 -- nearly 2x the next entry. At 2,533 LOC and 52 changes across 300 commits (17% of all commits touch it), this file is the single highest-risk maintenance target in the codebase. It changes with scheduler.py, context.py, tasks.py, workspace.py, activity.py, and tools/__init__.py. This is the God Object pattern in action.

---

## 3. Commit Pattern Analysis [VERIFIED]

### Commit Type Distribution (300 commits)

| Count | Type | % |
|-------|------|---|
| 120 | feat | 40% |
| 70 | fix | 23% |
| 28 | state | 9% |
| 28 | docs | 9% |
| 17 | status | 6% |
| 15 | chore | 5% |
| 12 | ops | 4% |
| 4 | test | 1% |
| 1 | refactor | 0.3% |
| 5 | other | 2% |

### Observations

- **Feature-dominant (40%):** The project is in active build phase, consistent with 86/86 manifest items done.
- **Fix ratio (23%):** Healthy -- roughly 1 fix per 2 features. Indicates iterative refinement rather than instability.
- **State/status commits (15%):** Session continuity overhead. These are session bookkeeping (STATUS.md, MEMORY.md updates).
- **Test commits (1%):** Critically low. Only 4 test-focused commits out of 300. Tests exist (10 test files) but are not being driven by their own commit cycle -- they are bundled into feat commits.
- **Refactor commits (0.3%):** One single refactor commit. The codebase is accumulating technical debt (see server.py churn) without dedicated refactoring passes.

---

## 4. Directory-level Coupling [VERIFIED]

### Top-level Directory Pairs

| Co-changes | Dir A | Dir B |
|------------|-------|-------|
| 28 | docs/BUILD-MANIFEST.md | projects/agents |
| 22 | projects/agents | projects/dashboard |
| 20 | ansible/roles | projects/agents |
| 19 | ansible/roles | docs/BUILD-MANIFEST.md |
| 18 | CLAUDE.md | docs/BUILD-MANIFEST.md |
| 16 | ansible/host_vars | ansible/roles |
| 15 | ansible/playbooks | ansible/roles |
| 15 | docs/BUILD-MANIFEST.md | projects/dashboard |
| 14 | CLAUDE.md | projects/agents |
| 14 | ansible/roles | projects/dashboard |

### Coupling Matrix (project-level, counts) [VERIFIED]

Self-change counts on diagonal. Off-diagonal = co-change frequency.

|  | ansible | docs | agents | dashboard | eoq | scripts |
|--|---------|------|--------|-----------|-----|---------|
| **ansible** | **49** | 27 | 20 | 14 | 3 | 16 |
| **docs** | 27 | **123** | 40 | 27 | 7 | 26 |
| **agents** | 20 | 40 | **102** | 22 | 6 | 22 |
| **dashboard** | 14 | 27 | 22 | **57** | 3 | 11 |
| **eoq** | 3 | 7 | 6 | 3 | **13** | 7 |
| **scripts** | 16 | 26 | 22 | 11 | 7 | **45** |

### Tightest Directory Couplings by Jaccard Similarity [VERIFIED]

Jaccard removes the bias of raw counts, revealing which pairs are *proportionally* coupled relative to their own change rates.

| Jaccard | Co-changes | Dir A | Dir B |
|---------|------------|-------|-------|
| 0.45 | 5 | ansible/host_vars/vault.yml | ansible/roles/vault-monitoring |
| 0.43 | 6 | ansible/roles/agents | projects/agents/docker-compose.yml |
| 0.23 | 8 | docs/SERVICES.md | docs/SYSTEM-SPEC.md |
| 0.22 | 28 | docs/BUILD-MANIFEST.md | projects/agents/src |
| 0.19 | 10 | projects/dashboard/src | projects/dashboard/tests |
| 0.16 | 20 | projects/agents/src | projects/dashboard/src |
| 0.16 | 12 | docs/BUILD-MANIFEST.md | docs/SERVICES.md |

---

## 5. Change Velocity [VERIFIED]

### Weekly Commit Volume

| Week | Commits |
|------|---------|
| 2026-W09 (Feb 23-28) | 87 |
| 2026-W10 (Mar 2-6) | 83 |
| 2026-W11 (Mar 7-14) | 130 |

- **Average: 100 commits/week** -- extremely high velocity.
- **Accelerating:** W11 is 50% higher than W09/W10 (sprint finishing energy).
- **All 300 commits span only 20 calendar days** (Feb 23 - Mar 14).

### Daily Distribution [VERIFIED]

| Date | Commits | |
|------|---------|---|
| Feb 23 | 2 | ## |
| Feb 24 | 33 | ################################# |
| Feb 25 | 24 | ######################## |
| Feb 26 | 28 | ############################ |
| *(gap: Feb 27 - Mar 6)* | — | |
| Mar 7 | 29 | ############################# |
| Mar 8 | 54 | ###################################################### |
| Mar 9 | 52 | #################################################### |
| Mar 10 | 15 | ############### |
| Mar 11 | 2 | ## |
| Mar 12 | 7 | ####### |
| Mar 13 | 17 | ################# |
| Mar 14 | 37 | ##################################### |

- **Peak:** 54 commits on Mar 8, 52 on Mar 9. These were marathon build sessions.
- **9-day gap** (Feb 27 - Mar 6) is notable -- either vacation, blocked, or working in other repos.
- **12 active days** produced 300 commits = 25 commits/active day average.

### Commit Granularity [VERIFIED]

- **Average: 10.9 files per commit** (last 100 commits).
- This is high. Typical open-source projects average 2-4 files/commit. The high count reflects:
  - Session-state bookkeeping (STATUS.md, MEMORY.md, BUILD-MANIFEST.md added to most commits)
  - Cross-cutting feature work (agent code + ansible deployment + docs in one commit)
  - Claude Code's tendency toward larger, complete-feature commits

---

## 6. Commit Isolation Analysis [VERIFIED]

| Category | Count | % |
|----------|-------|---|
| Single-zone commits | 140 | 46% |
| Cross-zone commits | 92 | 30% |
| Meta-only commits | 66 | 22% |

### Zone Participation

| Zone | Commits Touching | % of all |
|------|-----------------|----------|
| docs | 123 | 41% |
| root-meta | 113 | 37% |
| agents | 102 | 34% |
| dashboard | 57 | 19% |
| dotfiles | 55 | 18% |
| ansible | 49 | 16% |
| scripts | 45 | 15% |
| eoq | 13 | 4% |
| ulrich | 8 | 2% |

**30% of commits cross zone boundaries.** The primary cross-zone corridors are:
- agents <-> docs (40 co-changes)
- agents <-> ansible (20 co-changes)
- agents <-> dashboard (22 co-changes)
- docs <-> dashboard (27 co-changes)

---

## 7. Jaccard Temporal Coupling (Strongest File Pairs) [VERIFIED]

Jaccard similarity = co-changes / (changes_A + changes_B - co-changes). A score of 1.0 means the files *always* change together.

| Jaccard | Co-changes | File A | File B |
|---------|------------|--------|--------|
| 1.00 | 4 | visual-system/README.md | visual-system/ROUTE_DIRECTION_MEMO.md |
| 1.00 | 3 | agents/home.py | agents/media.py |
| 1.00 | 3 | dashboard defaults/main.yml | dashboard compose template |
| 0.80 | 4 | grafana-alerts tasks/main.yml | backup-alerts template |
| 0.75 | 6 | vault-litellm defaults | litellm_config template |
| 0.75 | 3 | ROUTE_DIRECTION_MEMO.md | TOKEN_SPEC.md |
| 0.60 | 3 | agents/general.py | agents/media.py |
| 0.60 | 3 | agents/general.py | agents/home.py |
| 0.60 | 3 | agents/data_curator.py | agents/general.py |
| 0.50 | 3 | preference_learning.py | self_improvement.py |
| 0.44 | 4 | agents defaults/main.yml | agents compose template |
| 0.44 | 4 | agents compose template | agents docker-compose.yml |
| 0.43 | 3 | diagnosis.py | self_improvement.py |
| 0.40 | 4 | agent-contracts.md | intelligence-layers.md |
| 0.36 | 4 | core.yml | interface.yml |

---

## 8. Natural Boundaries & Clusters

### Tightly Coupled Clusters (always change together)

**Cluster 1: Agent Runtime Core**
- `server.py`, `scheduler.py`, `context.py`, `tasks.py`, `workspace.py`, `workplanner.py`
- 52 commits touch server.py; scheduler (17), context (13), tasks (14) are its primary satellites.
- This cluster represents the core execution engine. server.py is the hub; any behavioral change radiates through the others.
- **Risk:** server.py at 2,533 LOC is a God Object. Its 106 unique co-change partners means nearly every subsystem passes through it.

**Cluster 2: Agent Intelligence Layer**
- `self_improvement.py`, `diagnosis.py`, `preference_learning.py`, `skill_learning.py`, `escalation.py`
- These change together but less frequently (5-7 changes each). They form a cohesive "meta-cognition" subsystem.
- Jaccard: self_improvement <-> preference_learning (0.50), self_improvement <-> diagnosis (0.43).

**Cluster 3: Agent Definitions**
- `agents/home.py`, `agents/media.py`, `agents/general.py`, `agents/data_curator.py`
- Jaccard 1.00 between home.py and media.py -- they always change as a batch.
- Batch updates to agent definitions (prompt changes, config changes) drive this coupling.

**Cluster 4: Ansible Deployment Units**
- Each Ansible role's `defaults/main.yml` + `templates/*.j2` + `tasks/main.yml` form tight triads.
- vault-litellm: J=0.75 between defaults and template.
- agents role: J=0.44 between defaults and compose template.
- grafana-alerts: J=0.80 between tasks and template.
- These are *healthy* coupling -- Ansible roles are designed to be self-contained units.

**Cluster 5: Dashboard Visual System**
- `visual-system/README.md`, `ROUTE_DIRECTION_MEMO.md`, `TOKEN_SPEC.md`, `globals.css`
- J=1.00 between README and ROUTE_DIRECTION_MEMO. All 4 files co-change.
- Design system documentation + implementation -- healthy coupling.

**Cluster 6: Session Bookkeeping**
- `CLAUDE.md`, `MEMORY.md`, `STATUS.md`, `BUILD-MANIFEST.md`
- These are the "meta" cluster. BUILD-MANIFEST has 148 unique co-change partners (highest in codebase).
- 22% of commits are meta-only. This is the overhead cost of session continuity.

### Loosely Coupled Zones (rarely interact)

| Zone A | Zone B | Co-changes | Assessment |
|--------|--------|------------|------------|
| projects/eoq | ansible | 3 | Independent app, correct |
| projects/ulrich-energy | ansible | 3 | Independent app, correct |
| projects/ws-pty-bridge | everything | 0-1 | Stable utility, correct |
| projects/gpu-orchestrator | everything | 0-2 | Rarely touched |
| evals | everything | 0-4 | Isolated evaluation suite |
| services/ | everything | 0-4 | Static docker configs |
| recipes/ | everything | 0-2 | Inert reference files |

These are *healthy* boundaries. EoQ, Ulrich Energy, and ws-pty-bridge are standalone applications that correctly maintain independence from the infrastructure core.

### Connector Files (change with many different clusters)

| Partners | File | Role |
|----------|------|------|
| 148 | docs/BUILD-MANIFEST.md | Work tracker -- touches everything by design |
| 129 | CLAUDE.md | Session config -- updated during feature work |
| 106 | server.py | God Object -- actual architectural connector |
| 88 | MEMORY.md | Session memory -- updated alongside work |
| 72 | docs/SERVICES.md | Service inventory -- updated on deploys |
| 66 | docs/SYSTEM-SPEC.md | Spec doc -- updated on infrastructure changes |
| 61 | STATUS.md | Session status |
| 61 | test_repo_contracts.py | Contract test -- validates cross-cutting concerns |
| 52 | ansible/playbooks/site.yml | Master playbook -- touched on any deploy |
| 50 | ansible/host_vars/core.yml | FOUNDRY config -- touched on infra changes |

The first 7 are documentation/meta files -- their high connectivity is by design (session continuity protocol requires updating them). The real architectural connectors are:

1. **server.py (106 partners):** The only code file in the top 10. This is the true bottleneck.
2. **test_repo_contracts.py (61 partners):** Contract test that validates cross-project consistency. High connectivity is correct for this role.
3. **site.yml (52 partners):** Ansible master playbook. Touched whenever any role changes. Correct for an orchestration file.

---

## 9. Summary Findings

### Architecture Health Signals

| Signal | Status | Evidence |
|--------|--------|----------|
| God Object | **server.py is critical risk** | 2,533 LOC, 52 changes, 106 co-change partners, churn score 131K |
| Healthy module boundaries | **Yes, outside agents** | EoQ, Ulrich, ws-pty-bridge are cleanly isolated |
| Ansible role cohesion | **Healthy** | defaults/templates/tasks triads couple tightly (J=0.44-0.80) |
| Test investment | **Underweight** | 1% of commits are test-focused; 10 test files for 37 agent modules |
| Refactoring investment | **Near zero** | 1 refactor commit in 300. Debt accumulates in server.py |
| Session overhead | **22% of commits** | Meta-only commits for STATUS/MEMORY/BUILD-MANIFEST |
| Cross-zone coupling | **30% of commits** | Moderate -- mostly agents<->docs and agents<->ansible |
| Commit granularity | **10.9 files/commit avg** | Large commits; session bookkeeping inflates this |
| Velocity | **100 commits/week** | Extremely high, 25/active day, accelerating |

### Top 3 Structural Risks

1. **server.py God Object:** At 2,533 LOC with 106 co-change partners, this file is the architectural bottleneck. Every subsystem flows through it. A single-file failure here affects everything. Decomposition would reduce coupling and churn.

2. **Test deficit:** 4 test-focused commits out of 300 (1%). The 10 test files exist but are not keeping pace with the 52 changes to server.py or the 17 to scheduler.py. Contract tests (test_repo_contracts.py) are the most active test file at 11 changes, but unit test coverage for the intelligence layer (self_improvement, diagnosis, preference_learning) appears minimal.

3. **Session bookkeeping overhead:** 22% of commits are meta-only (STATUS.md, MEMORY.md, BUILD-MANIFEST.md). The 10.9 files/commit average is inflated by these mandatory session-continuity updates. This is a structural cost of the Claude Code workflow -- not a bug, but worth recognizing as overhead.
