# Athanor Reference Context

This file is reference-only context for Athanor. It is not the live source of truth.

## Authority Model

Implementation authority: `C:\Athanor`

Runtime authority: `/home/shaun/repos/athanor` on `DEV`

Reference-only docs:
- [docs/archive/planning-era/VISION.md](/C:/Athanor/docs/archive/planning-era/VISION.md)
- [docs/MASTER-PLAN.md](/C:/Athanor/docs/MASTER-PLAN.md)
- [MEMORY.md](/C:/Athanor/MEMORY.md)
- this file

Archive criteria:
- keep only material still needed for operator intent, audit history, recovery evidence, or an active migration/cutover
- delete stale operational claims once equivalent truth exists in the registries or canonical current-state docs

## Use

Read this file for durable operator intent and working style. Do not use it for mutable runtime facts such as:
- current repo authority
- current node hardware
- active provider inventory
- live model deployment
- current service endpoints

Those facts now belong to:
- [STATUS.md](/C:/Athanor/STATUS.md)
- [docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md](/C:/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md)
- [docs/operations/ATHANOR-OPERATING-SYSTEM.md](/C:/Athanor/docs/operations/ATHANOR-OPERATING-SYSTEM.md)
- [config/automation-backbone](/C:/Athanor/config/automation-backbone)

## Durable Intent That Still Matters

- Shaun is a solo operator; optimize for low cognitive overhead and high leverage.
- Adult and NSFW workloads are valid first-class work.
- Runtime truth outranks memory and stale narrative docs.
- Cloud subscriptions should be used intentionally, but not on the basis of fake quota math.
- Sovereign or refusal-sensitive work stays local unless policy is explicitly changed.
- The dashboard and governor surfaces should be the primary control plane when healthy.

Any operational claim beyond that should move into canonical docs or registries and then be deleted from here.
