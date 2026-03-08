At the start of every session, read STATUS.md in the repo root. It contains cluster state, sprint progress, and next actions from the previous session.

At the end of every session or before compaction: update STATUS.md with what was done, update Next Actions, add a Session Log entry, then git add STATUS.md && git commit -m "status: update" && git push.

If STATUS.md doesn't exist, create it with a fresh cluster assessment.
