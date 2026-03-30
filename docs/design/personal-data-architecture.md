# Personal Data Architecture — Shaun's Second Brain

*Design Document | 2026-02-26*

## 1. The Problem

Shaun's digital life exists in fragments:

| Source | Location | Status | Content Type |
|--------|----------|--------|-------------|
| Windows C: drive | DEV /mnt/c | Accessible from WSL | Work docs, finance, bookmarks, configs |
| Windows D: drive | DEV /mnt/d | Accessible from WSL | ISOs, old configs, photo exports, empty ChatGPT scaffolding |
| Google Drive | Cloud | **Inaccessible** (needs OAuth) | Unknown volume — likely contains the REAL copies of SOVEREIGN_DUMP, MASTER LISTS, Facebook Data, UEA projects, old Hydra/Kaizen configs |
| GitHub | Cloud | Accessible via `gh` CLI | 21 repos, 46 starred repos |
| VAULT | NFS /mnt/vault/ | Accessible | Media library, service data, hydra/kaizen snapshots |
| Browser bookmarks | C:\Documents\ | Accessible | 740 bookmarks across 78 folders |
| AI conversations | Google Drive / scattered | Partially accessible | ChatGPT exports (ghost dirs on D:), Claude sessions |
| Agent memory | Qdrant + Redis | Live | 2484 knowledge chunks, 55 preferences, activity logs |

**Critical discovery:** The entire `D:\Users\Shaun\Desktop\ChatGPT Files\` directory tree is **empty scaffolding** — 22+ subdirectories with zero files. This means SOVEREIGN_DUMP_001, MASTER LISTS, Facebook Data, Online Data, UEA business data, performer databases, and UNRAID project docs exist **only in Google Drive**. The D: drive synced structure but not content.

**The actual unique personal data on local drives is ~1.75 GB.** This is not a big data problem. It's an organization, connection, and understanding problem.

---

## 2. What "Solved" Looks Like

Not "all files indexed." Instead:

### 2.1 Any Agent Can Answer "What Do You Know About X?"

Where X is a property address, a person, a project, a financial plan, a technology, a decision. The answer draws from files, commits, activity, bookmarks, and conversation history. Today: agents only know what's in their Qdrant collection and context injection window.

### 2.2 Cross-References Are Automatic

Ask about "Gladstone Village" and get:
- The ENERGY STAR testing spreadsheets (Work/Spreadsheets/)
- The construction plan PDFs (Work/Construction/)
- The field inspection photos (Desktop/ property folders — if nearby)
- The BKI Tracker entry (Downloads/BKI Tracker*.xlsx)
- The ENERGY STAR program requirements that apply (Work/EnergyStar/)
- Any related bookmarks (Homelab/AI Development, Work)

Today: these are unconnected files in 5 different folders.

### 2.3 Identity Coherence

The system understands Shaun as a **whole person**:
- **Professional:** Energy auditor (BKI, UEA). Properties in MN (Delano, Waconia, Corcoran, Rogers, Prior Lake). Colleague: Erik Kittilstved. Tools: Field-Inspect, ENERGY STAR MFNC checklists.
- **Builder:** Athanor (current), Hydra/Kaizen (previous iterations). Autotelic — building is the reward. Zetetic — seeking never resolves. Evening/weekend work pattern.
- **Interests:** AI/ML (21 repos, 46 stars), homelab infrastructure, adult content curation, gaming, media server management, OSINT/security research, creative AI (ComfyUI, image/video gen).
- **Financial:** Debt elimination strategy active. Specific accounts and priorities documented.
- **Digital:** 740 bookmarks mapping interest topology. Multiple AI platform accounts. Google Photos archive.

Today: fragments of this exist in profile.md, Qdrant preferences, and scattered docs. No unified model.

### 2.4 Temporal Awareness

"What was I working on in January?" pulls from:
- Git commits (code changes)
- Agent activity logs (what agents did)
- File modification dates (what docs changed)
- BKI Tracker entries (what jobs were active)
- Dashboard interactions (what was viewed)

Today: only git log provides temporal awareness.

### 2.5 Proactive Intelligence

The system doesn't wait to be asked:
- "3 versions of BKI Tracker exist — the Feb 16 version appears to be the latest."
- "Gladstone Village II has testing data from 3 different dates but no final report."
- "Your debt elimination plan references a $X payment — no confirmation of payment found."
- "You bookmarked 12 AI agent frameworks but only use LangGraph — archive or review?"

Today: agents are purely reactive with personal data.

---

## 3. Architecture — Five Layers

```
Layer 5: ACT        Agents use personal context to do work
Layer 4: SURFACE    Dashboard pages, proactive notifications, search
Layer 3: CONNECT    Entity extraction, Neo4j graph, cross-references
Layer 2: UNDERSTAND LLM classification, tagging, summarization
Layer 1: INDEX      Parse, chunk, embed, store in Qdrant
Layer 0: TRANSIT    Get data from sources to processing location
```

### Layer 0: Data Transit (DEPLOYED)

**Problem:** The Data Curator agent runs on FOUNDRY in Docker. It can only see mounted volumes. Personal data lives on Google Drive (2 accounts).

**Solution:** A two-stage sync pipeline.

```
Google Drive (2 accounts) ──rclone──→ DEV staging
                                          │
                                    rsync over SSH
                                          │
                                          ▼
                                FOUNDRY /opt/athanor/personal-data/
                                          │
                                   Docker volume mount
                                          │
                                          ▼
                                container /data/personal/ (read-only)
                                          │
                                   Data Curator Agent
```

**Implementation:**
- `scripts/sync-personal-data.sh` on DEV — rclone + rsync pipeline
- Runs as cron on DEV: `0 */6 * * *` (every 6 hours, aligned with curator schedule)
- Two rclone remotes: `personal-drive:` (30 GiB) + `uea-drive:` (7 GiB)
- DEV staging at `/home/shaun/data/personal/{personal-drive,uea-drive}/`
- rsync to FOUNDRY at `/opt/athanor/personal-data/`

**Estimated transfer:** ~37 GiB initial, <500 MB incremental.

### Layer 1: Parse & Index (DEPLOYED)

The Data Curator agent handles this. Already deployed with 7 tools:
- `scan_directory` — Discover files
- `parse_document` — Multi-format extraction (MD, TXT, JSON, CSV, PDF, DOCX, XLSX)
- `index_document` — Chunk → embed → Qdrant upsert
- `search_personal` — Semantic search
- `get_scan_status` — Progress tracking
- `analyze_content` — LLM analysis
- `sync_gdrive` — Trigger rclone

**Qdrant collection:** `personal_data`, 1024-dim Cosine, same embedding model as knowledge.

**What's missing from Layer 1:**
- ~~Bookmark parser (HTML → structured entries)~~ ✅ DONE — 727 in Qdrant + Neo4j
- ~~GitHub repo indexer (README + key files per repo)~~ ✅ DONE — 82 chunks in Qdrant, 67 repos in Neo4j
- Deduplication (content hash comparison across sources)
- Image metadata extraction (EXIF for photos — location, date, camera)

### Layer 2: Understand

**Not just indexing — comprehension.** Every indexed document should have:

| Field | Source | Example |
|-------|--------|---------|
| `category` | Auto-classified by path + LLM | `work_energy`, `finance`, `ai_system` |
| `summary` | LLM-generated, one paragraph | "Energy Star testing data for Gladstone Village II, 3 rounds of vent flow testing..." |
| `topics` | LLM-extracted | `["energy audit", "MFNC", "ventilation testing", "Gladstone Village"]` |
| `entities` | LLM-extracted | `{"people": ["Erik Kittilstved"], "places": ["Gladstone Village II"], "orgs": ["BKI"]}` |
| `dates` | LLM-extracted | `{"created": "2026-01-15", "references": ["2026-02-01"]}` |
| `relevance` | LLM-scored | `0.8` (how useful is this to Shaun right now?) |
| `duplicates` | Content hash match | `["downloads:BKI_Tracker_v3.xlsx", "work:BKI_Tracker.xlsx"]` |

**This transforms the Qdrant collection from a bag of text chunks into a structured knowledge layer.**

**Implementation:** Add an `analyze_and_index` pipeline that:
1. Parses the document
2. Sends first 4000 chars to the reasoning model with a structured extraction prompt
3. Stores extracted metadata in Qdrant payload alongside the embedding
4. Optionally creates Neo4j nodes (Layer 3)

**Cost:** ~30 seconds per document at local inference speed. For 200 unique documents: ~100 minutes total. Amortized over the 6-hour schedule cycle = negligible.

### Layer 3: Connect — The Entity Graph

**This is where the real value emerges.** Neo4j already has 30 infrastructure nodes. Extend it with personal data entities.

**New node types:**
```
(:Person {name, role, relationship})
(:Property {address, city, state, type})
(:Project {name, status, type})       // extends existing
(:Document {path, category, summary}) // extends existing
(:Topic {name})
(:Organization {name, type})
(:Bookmark {url, title, folder})
(:GitRepo {name, description, language, stars})
```

**New relationship types:**
```
(:Person)-[:WORKS_WITH]->(:Person)
(:Person)-[:AUDITED]->(:Property)
(:Property)-[:HAS_DOCUMENT]->(:Document)
(:Document)-[:MENTIONS]->(:Person|Property|Organization|Topic)
(:GitRepo)-[:RELATES_TO]->(:Topic)
(:Bookmark)-[:CATEGORIZED_AS]->(:Topic)
(:Project)-[:EVOLVED_FROM]->(:Project)  // Hydra → Kaizen → Athanor
```

**The "Gladstone Village" query then becomes:**
```cypher
MATCH (p:Property {name: "Gladstone Village II"})-[:HAS_DOCUMENT]->(d:Document)
OPTIONAL MATCH (d)-[:MENTIONS]->(person:Person)
OPTIONAL MATCH (d)-[:MENTIONS]->(org:Organization)
RETURN d.path, d.category, d.summary, collect(person.name), collect(org.name)
```

**This returns ALL related documents, people, and organizations in one graph traversal.** No keyword matching, no embedding similarity thresholds — structural relationships.

### Layer 4: Surface

**Dashboard: Personal Data page** (`/personal-data`)
- Semantic search bar (queries both Qdrant personal_data and Neo4j)
- Category browser (tree view: work > energy > Gladstone Village)
- Recently indexed feed
- Entity explorer (click a person → see all connected docs)
- Duplicate detector panel
- Sync status (last rclone run, last rsync, last index cycle)

**Context injection upgrade:**
Currently agents get: preferences + activity + knowledge + goals + patterns + conventions.
Add: **personal context** — when user asks about work, energy audits, finance, etc., inject relevant personal data snippets from the personal_data collection.

**Proactive notifications:**
The Data Curator's scheduled runs can generate notifications:
- "Found 5 new files in Google Drive sync"
- "Indexed 12 documents from Work/Spreadsheets"
- "Detected 3 potential duplicates"
- "Property 1142 Oakwood Lane has photos but no testing data"

### Layer 5: Act

**Agents use personal data to do actual work:**

| Agent | How It Uses Personal Data |
|-------|--------------------------|
| General Assistant | "Check if all properties with photos also have testing data" |
| Knowledge Agent | Searches personal_data collection alongside knowledge |
| Coding Agent | References old Hydra/Kaizen code patterns when building Athanor features |
| Research Agent | Cross-references bookmarks with current research topics |
| Media Agent | Knows Shaun's viewing preferences from personal archive |
| Creative Agent | References style preferences from old ComfyUI configs |
| Home Agent | Uses work schedule patterns to optimize automation timing |
| Data Curator | Continuously discovers, analyzes, indexes, deduplicates |

---

## 4. Data Source Inventory (Verified 2026-02-26)

### What's Real (unique, non-duplicate content)

| Category | Files | Size | Location | Format |
|----------|-------|------|----------|--------|
| Energy audit spreadsheets | ~56 | ~87 MB | C: Work, Downloads | XLSX |
| Construction plans | ~4 | ~373 MB | C: Work/Construction | PDF (large) |
| ENERGY STAR program docs | ~21 | ~12 MB | C: Work/EnergyStar | PDF |
| Architectural plans | ~65 | ~100 MB | C: Work/Plans | PNG |
| Field inspection photos | ~277 | ~580 MB | C: Desktop (10 property folders) | JPG |
| Finance docs | 1 | ~35 KB | C: Finance | DOCX |
| Twelve Words component | 1 | ~8 KB | C: Finance | JSX |
| Athanor reference docs | 8 | ~204 KB | C: Documents/Athanor-Reference | MD, JSON |
| Athanor strategic docs | ~8 | ~182 KB | C: Downloads | MD |
| Browser bookmarks | 1 | ~752 KB | C: Documents | HTML (740 URLs, 78 folders) |
| Chrome bookmarks backup | 1 | ~661 KB | C: Documents/ChromeBackup | JSON |
| ShareX configs | ~12 | ~204 KB | C: Documents/ShareX | JSON |
| BKI Tracker versions | ~5 | ~16 MB | C: Downloads | XLSX |
| Google Photos exports | ~1,100 | ~570 MB | D: Downloads | JPG/PNG |
| Old Athanor/AI docs | ~15 | ~200 KB | D: Downloads | MD |
| **Google Drive** | **???** | **???** | **Cloud** | **Unknown** |

**Total known local: ~1.75 GB unique, ~500 parseable documents**

### What's Ghost (empty scaffolding on D:)

These directories exist on D: but contain zero files — the content is in Google Drive:
- SOVEREIGN_DUMP_001 (22 subdirs — CEBP, ChloeReactApp, Sovereign Home Systems, Tdarr configs, deployment docs)
- MASTER LISTS (7 subdirs — AI tools, Adult content, Sovereign System, Tech, Unraid, Usenet)
- Online Data / Shaun Facebook Data (full Facebook export structure)
- UEA (8 multifamily project folders with subfolder structure)
- UNRAID_Project (hardware specs, scripts)
- performers, Me-1-001 (photos), Tech_Disciplines_Sheets_Kit

**This is the strongest argument for rclone OAuth.** The most personal, most valuable data isn't on any local drive.

### What's in GitHub (21 repos)

| Repo | Description | Relevance |
|------|-------------|-----------|
| athanor | This project | Active, fully indexed |
| kaizen | Previous AI system iteration | Historical — architecture decisions |
| reverie-dream-journal | Dream journal app | Personal project |
| BKI-Tracker | Energy audit tracking | Active work tool |
| airtight-iq-dl-forecasting-engine | Duct leakage forecasting | Active work tool |
| AuditForecaster | Audit prediction | Work tool |
| nvidia-gpu-comparison | GPU comparison tool | Reference |
| stash-explorer | Stash browser | Athanor ecosystem |
| performer-database-app | Performer DB | Adult content |
| darkweb-tools-directory | OSINT tools | Interest/reference |
| Gaming-Ideas | Game concepts | Creative |
| hydra | Oldest AI system iteration | Historical |
| AI-Dev-Control-Plane | AI development framework | Historical |
| Reverie | Dream journal (original) | Historical |
| buff-wrap-inspector | Inspection tool | Work |
| Buffalog | Logging tool | Utility |
| To-Do | Task management | Utility |
| website-app | Personal website | Personal |
| system-bible | System documentation | Historical reference |
| ulrich-energy-auditing | UEA business | Work |
| Favorites | Curated list | Reference |

### The 740 Bookmarks — Interest Topology

The bookmarks reveal Shaun's complete interest graph:
- **Work:** Energy auditing (Finance, Insurance, IT, EE, Other Raters)
- **Homelab:** AI Development, Benchmarks, Database, Monitoring, Network, Models, Research
- **Security/OSINT:** Dark, Hacking, OSINT & Social, Pen Testing, Webcrawl
- **Media:** Docker Containers, Downloading, Streaming (Sports, Docs, General)
- **Adult:** Streaming, Torrents, Games, Forums, OF Leaks, Tube, Film Databases, Performers
- **Personal:** Finances (Health, Insurance, Investments, Loans, Utilities), Home Projects (Gym, Landscaping, Hydroponics, Woodworking), Engagement/Wedding
- **Gaming:** Dedicated folder
- **Usenet:** NewsReader, Provider, Indexer

**This is the densest signal of who Shaun is.** 740 URLs organized into 78 folders. Parsing this into Neo4j creates an instant interest/knowledge map.

---

## 5. The Bookmark Insight

The bookmarks deserve special attention because they're the **cheapest, highest-signal data source**. One 752 KB HTML file contains:

1. **Professional network topology** — which energy auditing sites, which training resources, which tools
2. **Technical skill map** — which AI frameworks bookmarked, which databases studied, which monitoring tools evaluated
3. **Project history** — what was being researched when
4. **Interest intensity** — folder depth and bookmark count per topic signals how deep each interest goes
5. **Hidden connections** — a bookmark in "Homelab" that relates to something in "Work" reveals cross-pollination

**Proposed treatment:**
1. Parse HTML into structured JSON (url, title, folder_path, add_date)
2. Each bookmark becomes a Neo4j `:Bookmark` node
3. Folder hierarchy becomes `:Topic` nodes with `:SUBCATEGORY_OF` relationships
4. Fetch page titles/descriptions for bookmarks where title is missing
5. LLM-classify each bookmark into Athanor-relevant categories
6. Connect to existing `:Project`, `:Agent`, `:Service` nodes where relevant

**Result:** `MATCH (b:Bookmark)-[:CATEGORIZED_AS]->(t:Topic)<-[:RELATES_TO]-(r:GitRepo) RETURN ...` — find which bookmarks relate to which projects.

---

## 6. The Deduplication Problem

From the inventory:

| File Pattern | Copies Found | Locations |
|-------------|-------------|-----------|
| BKI Tracker*.xlsx | 5+ versions | C: Downloads (5), D: Downloads (?) |
| Carver Oaks testing*.xlsx | 7+ versions | C: Work, C: Downloads, D: Downloads |
| Gladstone Village*.xlsx | 3+ versions | C: Work, C: Downloads, D: Downloads |
| Construction CD sets (PDF) | 2-3 copies | C: Work, C: Desktop, D: Downloads |
| twelve-words.jsx | 3 copies | C: Finance (3 identical) |
| Facebook Data export | 2 directory trees | D: Online Data, D: Shaun Facebook Data (both empty) |
| Google Photos exports | Multiple sets | C: Downloads, D: Downloads |

**Strategy:**
1. **Content hash every file** during indexing (already implemented in index_document)
2. **Group by hash** — identical content gets one canonical entry
3. **Version detection** — similar filenames with different hashes = versions
4. **Latest wins** — most recently modified version is canonical
5. **Report duplicates** — dashboard shows duplicate groups for Shaun to review
6. Don't delete anything — just mark canonical vs duplicate in metadata

---

## 7. The Google Drive Gap

The empty D: drive scaffolding tells us Google Drive likely contains:

| Folder | Expected Content | Value |
|--------|-----------------|-------|
| SOVEREIGN_DUMP_001 | Full ChatGPT conversation exports, AI project files, deployment docs | **Critical** — AI system history |
| MASTER LISTS | Curated lists: AI tools, adult content, tech, Usenet | **High** — interest mapping |
| Online Data / Facebook Data | Facebook profile export (ads, connections, preferences, activity) | **Medium** — social graph |
| UEA | Multifamily energy audit projects (8 properties with photos/data) | **Critical** — work history |
| UNRAID_Project | Original UNRAID/Hydra hardware specs and scripts | **High** — system history |
| performers | Performer database | **Low** (Stash handles this now) |

**Without Google Drive, we're missing ~40% of the personal data story.** The local drives have work output (spreadsheets, plans, photos). Google Drive has the thinking, planning, and personal data.

**Required action from Shaun:** Run `~/.local/bin/rclone config` → New remote → Google Drive → Browser OAuth. One-time, 2 minutes.

---

## 8. Photo Strategy

**277 field inspection photos + ~1,700 Google Photos = ~2,000 images**

Today: opaque binary blobs. No text extraction, no description, no connection to projects.

**Phase 1 (now):** Extract EXIF metadata — GPS coordinates, timestamps, camera info. Store as structured Qdrant payload. Connect property photos to property addresses via folder name.

**Phase 2 (when Qwen3.5-27B deploys on vLLM 0.17+):** The multimodal VLM can describe images. Send each photo through the model:
- Field photos: "Ductwork in attic, visible insulation gaps, HVAC unit model visible"
- Construction plans: OCR text from blueprint annotations
- Personal photos: "Two people at a restaurant, outdoor seating"

This turns every photo into searchable text. "Find photos of ductwork problems" actually works.

**Phase 3 (future):** Image embeddings in a separate Qdrant collection for visual similarity search. "Find photos similar to this one."

---

## 9. GitHub Integration

21 repos are a goldmine of project history. Index:

1. **README.md** from each repo — project description, purpose, status
2. **Key config files** — package.json, pyproject.toml, docker-compose.yml (reveals tech stack)
3. **Commit history** — summarize major changes per repo
4. **Issues/PRs** — if any, capture discussion context

**Implementation:** Use `gh` CLI to pull repo metadata, clone key files, index into knowledge or personal_data collection. One-time script, re-run monthly.

**The 46 starred repos** are equally valuable as interest signals. Each star = "this matters to Shaun." Fetch repo descriptions, categorize, create `:GitRepo` nodes in Neo4j.

---

## 10. Phase Plan

### Phase 1: Transit Script ✅ COMPLETE (2026-02-26)
- ✅ `scripts/sync-personal-data.sh` — selective rsync from DEV → Node 1 (not VAULT — SSH limitations)
- ✅ Synced 632 MB: 609 MB photos (10 property folders), 21 MB downloads, 1.6 MB docs, 228 KB configs
- ✅ Supports `--dry-run`, `--stats`, `-h`
- ✅ Volume-mounted read-only in agent container at `/data/personal/`
- ✅ Cron on DEV: `0 */6 * * *`
- Note: Work/ and Finance/ dirs not found at expected Desktop path — may be elsewhere

### Phase 2: Bookmark Parser ✅ COMPLETE (2026-02-26)
- ✅ Parse `bookmarks_2_16_26.html` into structured JSON (`docs/data/bookmarks.json`)
- ✅ Index 727 unique bookmarks into Qdrant `personal_data` (740 total, 13 URL dedupes)
- ✅ Create Neo4j :Bookmark (727) and :Topic (78) nodes
- ✅ 77 SUBCATEGORY_OF + 690 CATEGORIZED_AS relationships
- Scripts: `scripts/parse-bookmarks.py`, `scripts/graph-bookmarks.py`

### Phase 3: Initial Bulk Index ✅ COMPLETE (2026-02-26)
- ✅ Data Curator deployed with read access to `/data/personal/` (12 photo dirs, 2 download dirs, docs, configs)
- ✅ `scripts/index-files.py` indexed 119/121 parseable files (XLSX, PDF, MD, JSON, configs) → 1,511 new Qdrant chunks
- ✅ Categories: work_energy (spreadsheets), athanor_docs (reference/bootstrap), athanor_reference, configs (ShareX)
- ✅ Content hash for incremental re-indexing (`--force` to re-index all)
- Remaining: LLM-classify per-file summaries, identify duplicates
- Google Drive content still blocked (needs rclone OAuth)

### Phase 4: GitHub Integration ✅ COMPLETE (2026-02-26)
- ✅ Indexed 21 owned repos (metadata + 15 READMEs) into Qdrant `personal_data`
- ✅ Indexed 46 starred repos as interest signals
- ✅ Created 67 Neo4j :GitRepo nodes + 283 GitHub :Topic nodes + 501 RELATES_TO relationships
- ✅ Evolution chain: hydra → kaizen → athanor
- Scripts: `scripts/index-github.py`, `scripts/graph-github.py`
- Cached data: `docs/data/github-repos.json`

### Phase 5: Google Drive (needs Shaun)
- Shaun completes rclone OAuth
- Initial sync to VAULT
- Scheduled sync every 6 hours
- Data Curator indexes new Google Drive content

### Phase 6: Entity Extraction ✅ COMPLETE (2026-02-26)
- ✅ `scripts/extract-entities.py` — LLM-powered extraction from all 793 Qdrant points (0 errors)
- ✅ Qwen3.5-35B-A3B with thinking disabled (`enable_thinking: false`, `max_tokens: 2000`) for reliable JSON output
- ✅ Neo4j final: 3,095 nodes (1055 Topics, 701 Documents, 391 Orgs, 97 People, 67 GitRepos, 24 Services, 18 Places)
- ✅ 4,447 relationships (3139 MENTIONS, 685 CATEGORIZED_AS, 501 RELATES_TO, 77 SUBCATEGORY_OF)
- ✅ Incremental support (skips already-extracted points)
- ✅ Constraints: Person, Organization, Place name uniqueness; Document doc_id uniqueness; Topic name index

### Phase 7: Dashboard Page ✅ COMPLETE (2026-02-26)
- ✅ `/personal-data` page deployed on the Athanor Command Center at `https://athanor.local/` (runtime fallback `http://dev.athanor.local:3001/`)
- ✅ Semantic search (LiteLLM embedding → Qdrant vector search)
- ✅ Category overview with subcategory breakdown and percentage bars
- ✅ Knowledge graph summary (Neo4j: node/relationship counts, labels, top topics)
- ✅ Recently indexed items feed
- ✅ Stats API: `/api/personal-data/stats` (GET), `/api/personal-data/search` (POST)
- ✅ Navigation: sidebar + /more mobile overflow

### Phase 8: Photo Analysis (after Qwen3.5 deploys)
- EXIF extraction for all photos
- VLM description generation
- Visual similarity search

### Phase 9: Context Injection Upgrade ✅ COMPLETE (2026-02-26)
- ✅ Added `personal_limit` to `AGENT_CONTEXT_CONFIG` for all 8+1 agents
- ✅ Parallel Qdrant query on `personal_data` collection in `enrich_context()`
- ✅ 6 agents receive personal data: general-assistant (3), knowledge (5), research (3), data-curator (5), home (2), coding (2)
- ✅ Agents with `personal_limit: 0` skip the query entirely (zero overhead)

### Phase 10: Proactive Intelligence
- Data Curator generates insight notifications
- Duplicate alerts, missing data alerts, deadline detection
- Weekly personal data digest

---

## 11. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Qdrant personal_data points | **2,304** (727 bookmarks + 66 GitHub + 1,511 file chunks) ✅ | 3,000+ (after Google Drive) |
| Google Drive files accessible | 0 | All (blocked on rclone OAuth) |
| Neo4j nodes | **3,095** (1055 Topics, 701 Documents, 391 Orgs, 97 People, 67 GitRepos, 24 Services, 18 Places) ✅ | 4,000+ (after Google Drive) |
| Neo4j relationships | **4,447** (3139 MENTIONS, 685 CATEGORIZED_AS, 501 RELATES_TO, 77 SUBCATEGORY_OF, 45 infra) ✅ | 5,000+ |
| Bookmark topics mapped | **78 folders, 727 URLs** ✅ | 78 folders, 740 URLs |
| GitHub repos indexed | **67 repos (21 owned + 46 starred)** ✅ | 21 repos + 46 stars |
| Synced personal data | **632 MB** (photos, downloads, docs, configs) ✅ | 1.75 GB (full local) |
| Files content-indexed | **119/121** (XLSX, PDF, MD, JSON, configs) ✅ | All parseable files |
| Photo descriptions | 0 | 2,000 (Phase 8, needs Qwen3.5-VLM) |
| Duplicate groups identified | 0 | 20+ |
| Semantic search accuracy | **Working** (bookmarks + GitHub + file content, cross-domain) ✅ | All personal docs |
| Agent context quality | **Deployed** (6 agents get personal data) ✅ | All relevant agents |
| Dashboard page | **Live** (`https://athanor.local/personal-data`) ✅ | Full entity explorer |
| Data Curator file access | **Working** (/data/personal/ read-only) ✅ | Auto-index on schedule |

---

## 12. Dependencies and Blockers

| Blocker | Blocks | Resolution |
|---------|--------|-----------|
| ~~VAULT unreachable~~ | ~~Phase 1, 3~~ | ✅ Resolved: sync targets Node 1 directly |
| rclone OAuth (Shaun) | Phase 5 (Google Drive) | Shaun runs `~/.local/bin/rclone config` |
| vLLM 0.17+ (Qwen3.5-VLM) | Phase 8 (photo analysis) | Upstream release |
| Work/Finance dir paths | Phase 1 completeness | Verify actual paths on C: drive |

---

## 13. Architectural Decisions

**Q: Why not a separate tool (Khoj, RAGFlow, n8n)?**
A: Athanor already has the complete stack: vector DB, graph DB, LLM inference, agent framework, scheduler, dashboard. Adding a separate tool creates a parallel system that doesn't integrate with agent context injection, doesn't feed the knowledge graph, and adds maintenance burden. See `docs/research/2026-02-26-personal-data-agent.md`.

**Q: Why Qdrant `personal_data` collection and not just add to `knowledge`?**
A: Separation of concerns. Knowledge is curated project documentation. Personal data is raw life data. Different retention policies, different access patterns, different sensitivity levels. Agents can query either or both.

**Q: Why rsync to Node 1 and not VAULT?**
A: VAULT SSH doesn't support direct rsync connections. Node 1 has passwordless SSH from DEV and runs the agent container. Data is volume-mounted read-only at `/data/personal/`. Tradeoff: data doesn't survive Node 1 rebuilds, but re-sync is fast (632 MB, ~2 min). Consider VAULT NFS mount as secondary backup path once VAULT SSH is fixed.

**Q: Why not index images now?**
A: No multimodal model deployed yet. EXIF extraction is possible but low value without visual understanding. Qwen3.5-27B (waiting on vLLM 0.17+) unlocks this properly. Photos are the biggest potential value but need the right model.

**Q: Why bookmarks first?**
A: Highest signal-to-effort ratio. One 752 KB file → 740 categorized interest signals → complete interest topology in Neo4j. No external dependency, no sync needed, no LLM required for initial parsing.

---

*Last updated: 2026-02-26*
