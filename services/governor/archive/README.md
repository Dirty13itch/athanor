Legacy governor SQLite artifacts no longer live in the implementation-authority tree.

- The retired `governor.db` snapshot was deleted after the compatibility-facade cutover.
- The legacy `dispatch.py` helper is deleted from the active tree; git history is the only remaining reference.
- No SQLite governor artifact remains as active or archived repo truth.
- Canonical task state now lives in Redis through the agent server `/v1/tasks` APIs.
