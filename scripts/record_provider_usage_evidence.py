from __future__ import annotations

import argparse
from pathlib import Path

from provider_usage_evidence import (
    append_capture,
    load_catalog_provider,
    utc_now,
)
from truth_inventory import PROVIDER_USAGE_EVIDENCE_PATH


ALLOWED_STATUSES = {"observed", "verified", "not_supported", "auth_failed", "request_failed"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Record provider-specific usage evidence for weak provider lanes.")
    parser.add_argument("--provider-id", required=True)
    parser.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    parser.add_argument("--source", required=True, help="Runtime surface or evidence source, e.g. vault-litellm-logs")
    parser.add_argument("--proof-kind", default="litellm_alias_request")
    parser.add_argument("--observed-at", default=utc_now())
    parser.add_argument("--alias", help="Alias exercised, if distinct from catalog")
    parser.add_argument("--requested-model", help="Requested served model id or alias used for the proof.")
    parser.add_argument("--response-model", help="Response model id returned by LiteLLM, if present.")
    parser.add_argument("--matched-by", help="How the requested model was selected, e.g. preferred_exact or token:qwen.")
    parser.add_argument("--http-status", type=int, help="HTTP status returned by the probe request.")
    parser.add_argument("--error-snippet", help="Short upstream error detail when the request did not succeed.")
    parser.add_argument("--request-surface", help="Path or command that produced the evidence")
    parser.add_argument("--note", action="append", default=[], help="Optional note; can be repeated")
    parser.add_argument("--write", type=Path, default=PROVIDER_USAGE_EVIDENCE_PATH)
    args = parser.parse_args()

    provider = load_catalog_provider(args.provider_id)
    evidence = dict(provider.get("evidence") or {})
    if str(evidence.get("kind") or "") != "vault_litellm_proxy":
        raise SystemExit(f"Provider {args.provider_id} does not use the vault_litellm_proxy evidence contract")

    proxy = dict(evidence.get("proxy") or {})
    alias = args.alias or str(proxy.get("alias") or "")
    if not alias:
        raise SystemExit(f"Provider {args.provider_id} is missing an alias in the provider catalog")

    capture = {
        "provider_id": args.provider_id,
        "status": args.status,
        "alias": alias,
        "requested_model": str(args.requested_model or "").strip() or None,
        "response_model": str(args.response_model or "").strip() or None,
        "matched_by": str(args.matched_by or "").strip() or None,
        "http_status": args.http_status,
        "error_snippet": str(args.error_snippet or "").strip() or None,
        "proof_kind": args.proof_kind,
        "observed_at": args.observed_at,
        "source": args.source,
        "request_surface": args.request_surface,
        "notes": [str(note).strip() for note in args.note if str(note).strip()],
    }
    append_capture(capture, path=args.write)
    print(f"Wrote {args.write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
