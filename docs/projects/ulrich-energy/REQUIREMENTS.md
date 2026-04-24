# Ulrich Energy — Requirements Document

*RESNET-certified HERS Rating business. HVAC workflow automation powered by Athanor.*

**Status:** Retired lineage reference only. The active delivery authority is `C:\Users\Shaun\Ulrich Energy Auditing Website`; this document is historical Athanor scaffold context and must not be treated as the live website plan.

Last updated: 2026-04-20

---

## Overview

Ulrich Energy performs home energy audits (HERS ratings) for residential construction in the Twin Cities. This project automates the workflow from field inspection through report delivery, using Athanor's AI inference stack for report generation and data analysis.

## Core Workflows

### 1. Field Inspection Data Entry (MVP)

**User:** Shaun (inspector) on phone/tablet in the field

**Flow:**
1. Create new inspection job (address, builder, inspector, date)
2. Enter structured data per inspection section:
   - Blower door test results (CFM50, ACH50)
   - Duct leakage test results (CFM25)
   - Insulation R-values by location (attic, walls, floor)
   - Window specs (U-factor, SHGC, frame type)
   - HVAC specs (equipment model, AFUE/SEER/HSPF, duct location)
   - Building envelope (orientation, sq ft, ceiling height, stories)
3. Upload photos (camera capture) with auto-tagging
4. Save draft / submit for report generation

**Data model:**
```
Job
├── id, address, builder, inspector, created_at, status
├── BuildingEnvelope: orientation, sqft, ceiling_height, stories, foundation_type
├── BlowerDoor: cfm50, ach50, enclosure_area, pass_fail
├── DuctLeakage: cfm25_total, cfm25_outside, test_method
├── Insulation[]: location, r_value, type, depth, notes
├── Windows[]: location, u_factor, shgc, frame_type, count, area
├── HVAC[]: system_type, model, capacity, efficiency_rating, duct_location
├── Photos[]: filename, section, caption, uploaded_at
└── Report: generated_at, pdf_path, hers_index, status
```

### 2. Report Generation

**Trigger:** Inspector submits completed inspection

**Process:**
1. Validate all required fields present
2. Generate report narrative via LLM (cloud model for quality):
   - Energy efficiency summary (homeowner-friendly language)
   - Test results with context ("Your blower door result of X CFM50 means...")
   - Recommended improvements ranked by cost-effectiveness
   - Compliance summary (if code inspection)
3. Format to PDF with Ulrich Energy branding
4. Store PDF, update job status

**LLM routing:** Cloud models (claude/gpt) for client-facing reports. Quality matters more than cost here.

### 3. Client Communication

**Flow:**
1. Send report PDF via email to client/builder
2. Generate follow-up emails (scheduling, preparation instructions)
3. Template-based with LLM personalization

### 4. Analytics Dashboard

**Views:**
- Jobs by status (draft, submitted, reported, delivered)
- Average HERS Index by builder
- Common failure patterns (blower door, duct leakage thresholds)
- Revenue tracking (jobs × rate)

---

## Technical Architecture

### Stack
- **Frontend:** Next.js (same stack as Command Center dashboard)
- **Backend:** Next.js API routes
- **Database:** PostgreSQL (dedicated, on VAULT)
- **File storage:** Local filesystem or MinIO (VAULT)
- **PDF generation:** Puppeteer or react-pdf
- **AI:** LiteLLM proxy → cloud models for reports, local models for classification

### API Routes

```
POST   /api/jobs              — Create new inspection job
GET    /api/jobs              — List jobs (with filters)
GET    /api/jobs/:id          — Get job details
PUT    /api/jobs/:id          — Update job data
POST   /api/jobs/:id/photos   — Upload inspection photos
POST   /api/jobs/:id/generate — Generate report
GET    /api/jobs/:id/report   — Download report PDF
POST   /api/jobs/:id/deliver  — Email report to client
GET    /api/analytics         — Dashboard analytics
```

### Database Schema (PostgreSQL)

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address TEXT NOT NULL,
    builder TEXT,
    inspector TEXT DEFAULT 'Shaun',
    status TEXT DEFAULT 'draft',  -- draft, submitted, reported, delivered
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE building_envelope (
    job_id UUID REFERENCES jobs(id),
    orientation TEXT,
    sqft NUMERIC,
    ceiling_height NUMERIC,
    stories INTEGER,
    foundation_type TEXT,
    PRIMARY KEY (job_id)
);

CREATE TABLE blower_door (
    job_id UUID REFERENCES jobs(id),
    cfm50 NUMERIC,
    ach50 NUMERIC,
    enclosure_area NUMERIC,
    pass_fail BOOLEAN,
    PRIMARY KEY (job_id)
);

CREATE TABLE duct_leakage (
    job_id UUID REFERENCES jobs(id),
    cfm25_total NUMERIC,
    cfm25_outside NUMERIC,
    test_method TEXT,
    PRIMARY KEY (job_id)
);

CREATE TABLE insulation (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    location TEXT,
    r_value NUMERIC,
    type TEXT,
    depth NUMERIC,
    notes TEXT
);

CREATE TABLE windows (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    location TEXT,
    u_factor NUMERIC,
    shgc NUMERIC,
    frame_type TEXT,
    count INTEGER DEFAULT 1,
    area NUMERIC
);

CREATE TABLE hvac_systems (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    system_type TEXT,  -- furnace, AC, heat_pump, etc
    model TEXT,
    capacity TEXT,
    efficiency_rating TEXT,  -- AFUE/SEER/HSPF value
    duct_location TEXT
);

CREATE TABLE photos (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    filename TEXT NOT NULL,
    section TEXT,
    caption TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reports (
    job_id UUID REFERENCES jobs(id),
    hers_index INTEGER,
    narrative TEXT,
    pdf_path TEXT,
    generated_at TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'draft',
    PRIMARY KEY (job_id)
);
```

---

## Reliability Requirements

- This is a **business application**. Reliability > features.
- Cloud model fallback is required for report generation.
- Data must be backed up (PostgreSQL on VAULT, included in appdata backup).
- Mobile-first UI — used on phone/tablet in the field.
- Offline-capable data entry (PWA with sync).

---

## Integration Points

| System | Integration |
|--------|------------|
| LiteLLM | Report narrative generation (cloud models preferred) |
| Email | Report delivery (SMTP or SendGrid) |
| Calendar | Scheduling via Google Calendar API or HA |
| VAULT PostgreSQL | Data persistence |
| Dashboard | Analytics display (optional Command Center integration) |

---

## MVP Scope (Phase 1)

1. Job CRUD with structured data entry
2. Photo upload
3. LLM report generation → PDF
4. Job list with status filters
5. Mobile-responsive UI

## Phase 2

6. Email delivery
7. Analytics dashboard
8. Calendar integration
9. Offline PWA sync
10. Builder/neighborhood pattern analysis
