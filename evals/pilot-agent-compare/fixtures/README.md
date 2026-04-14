# Pilot Fixture Contracts

This directory is reserved for concrete fixture artifacts that feed formal pilot comparisons without requiring live runtime mutation.

Current expected files:

- `agt-native-decision-trace.json`
- `agt-bridge-decision-trace.json`

These fixture files should capture one bounded approval-gated policy decision in two forms:

1. Native Athanor enforcement
2. AGT-backed bridge enforcement

Each trace should be safe to keep in source control and should contain:

- `trace_id`
- `scenario_id`
- `request_surface`
- `policy_class`
- `decision_summary`
- `decision_reason`
- `allowed_actions`
- `blocked_actions`
- `command_decision_record_ref`
- `operator_stream_event_ref`

Do not create placeholder success traces just to satisfy readiness. The files should remain absent until a real narrow bridge slice can emit representative evidence.

The formal preflight validates this required field set directly. If a trace file exists but omits any required field, the AGT lane stays blocked with `invalid_fixture:` instead of advancing to manual review.

The first accepted fixture pair is the bounded `approval-held-mutation` scenario. Those traces are allowed to be contract-level manual-review evidence as long as they stay narrow, preserve the native approval hold, and point back to the live Athanor decision and audit contracts instead of inventing a second control plane.
