import asyncio
import json
from athanor_agents.bootstrap_state import build_bootstrap_runtime_snapshot

async def main():
    snapshot = await build_bootstrap_runtime_snapshot(include_snapshot_write=True)
    print(json.dumps({
        'active_family': snapshot.get('active_family'),
        'next_slice_id': snapshot.get('next_slice_id'),
        'open_blockers': snapshot.get('open_blockers'),
        'waiting_on_approval_slice_id': snapshot.get('waiting_on_approval_slice_id'),
        'ready': snapshot.get('takeover_status', {}).get('ready'),
        'criteria': snapshot.get('takeover_status', {}).get('criteria'),
    }, indent=2))

asyncio.run(main())
