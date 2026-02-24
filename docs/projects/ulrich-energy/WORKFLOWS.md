# Ulrich Energy — Workflow Designs

*RESNET-certified HERS Rating business. Athanor integration planned.*

**Status:** Active business (S-Corp). Workflows designed, not yet implemented.

---

## Workflow 1: Inspection Report Generation

```
Field inspection (phone/tablet)
  → Structured data entry: blower door results, duct leakage,
    insulation R-values, window specs, HVAC specs, orientation, square footage
  → Upload photos of key findings (insulation gaps, air sealing issues, ductwork)
  → LLM generates professional report:
    - HERS Index calculation (may need REM/Rate or Ekotrope integration)
    - Energy efficiency summary for homeowner
    - Recommended improvements with estimated cost/savings
    - Compliance summary (if code inspection)
  → PDF output formatted to Ulrich Energy branding
  → Email to client with attachments
```

**Routing:** Report generation uses cloud models (content is professional/technical). Photo analysis could use local vision model (faster) or cloud (better quality). The LLM doesn't replace the HERS calculation software — it wraps the results in a professional narrative.

---

## Workflow 2: Scheduling and Client Communication

```
Client inquiry (phone, email, web form)
  → General Assistant classifies request type
  → Checks calendar availability
  → Generates response: scheduling confirmation, pricing info, preparation instructions
  → Sends via preferred channel (email, text)
```

---

## Workflow 3: Inspection Data Analysis

```
Accumulated inspection data (across all jobs)
  → Pattern recognition: common failure points by neighborhood, builder, vintage
  → Report: "Homes built by [builder] in [neighborhood] consistently fail blower door
    at [location] — recommend pre-drywall inspection emphasis on [area]"
  → Competitive intelligence: average HERS Index by building type in the Twin Cities
```

---

## Workflow 4: Business Administration

```
Invoice generation → QuickBooks integration (if available) or standalone PDF
Expense tracking → receipt scanning via phone camera → categorization
Mileage logging → GPS-based automatic tracking or manual entry
Annual tax prep → compiled expenses, revenue, mileage for S-Corp filing
```

---

## Infrastructure Needs

- These workflows don't need dedicated GPU — they run on existing agents
- A "Business Agent" could be added to the roster, or the General Assistant handles it with right tool access
- Calendar integration via Home Assistant or direct Google Calendar API
- Client database: simple SQLite or Airtable-style interface
- **Reliability matters more here than for personal projects.** Cloud fallback is preferred for anything client-facing.
