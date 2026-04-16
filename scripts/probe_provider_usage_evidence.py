from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

from provider_usage_evidence import (
    append_capture,
    choose_served_model,
    classify_probe_failure,
    iter_vault_proxy_provider_ids,
    litellm_base_url,
    litellm_headers,
    list_served_models,
    load_catalog_provider,
    proxy_probe_metadata,
    resolve_litellm_api_key,
    utc_now,
)
from truth_inventory import PROVIDER_USAGE_EVIDENCE_PATH


def _short_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return response.text.strip()[:240]
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error)[:240]
    return str(payload)[:240]


def _capture_for_missing_model(provider_id: str, alias: str, notes: list[str], base_url: str, matched_by: str) -> dict[str, object]:
    return {
        "provider_id": provider_id,
        "status": "not_supported",
        "alias": alias,
        "requested_model": None,
        "response_model": None,
        "matched_by": matched_by,
        "http_status": 200,
        "error_snippet": "No currently served model id matched the provider evidence contract.",
        "proof_kind": "litellm_model_inventory_scan",
        "observed_at": utc_now(),
        "source": "vault-litellm-live-probe",
        "request_surface": f"GET {base_url}/v1/models",
        "notes": notes,
    }


def _probe_provider(
    provider_id: str,
    *,
    client: httpx.Client,
    api_key: str,
    base_url: str,
    served_models: list[str],
    extra_notes: list[str],
) -> dict[str, object]:
    provider = load_catalog_provider(provider_id)
    alias, preferred_models, match_tokens = proxy_probe_metadata(provider)
    selected_model, matched_by = choose_served_model(provider, served_models)
    if not selected_model:
        notes = [
            f"Catalog alias `{alias}` did not resolve to a currently served LiteLLM model id.",
            f"Preferred models tried: {preferred_models or ['none']}.",
            f"Match tokens tried: {match_tokens or ['none']}.",
            *extra_notes,
        ]
        return _capture_for_missing_model(provider_id, alias, notes, base_url, matched_by)

    request_surface = f"POST {base_url}/v1/chat/completions"
    notes = list(extra_notes)
    try:
        response = client.post(
            f"{base_url}/v1/chat/completions",
            headers=litellm_headers(api_key),
            json={
                "model": selected_model,
                "messages": [{"role": "user", "content": "Reply with OK only."}],
                "temperature": 0,
                "max_tokens": 4,
            },
        )
    except httpx.HTTPError as exc:
        notes.insert(0, f"Probe request errored for requested model `{selected_model}`.")
        return {
            "provider_id": provider_id,
            "status": "request_failed",
            "alias": alias,
            "requested_model": selected_model,
            "response_model": None,
            "matched_by": matched_by,
            "http_status": None,
            "error_snippet": str(exc)[:240],
            "proof_kind": "litellm_model_completion",
            "observed_at": utc_now(),
            "source": "vault-litellm-live-probe",
            "request_surface": request_surface,
            "notes": notes,
        }
    error_snippet = None
    response_model = None
    try:
        payload = response.json()
    except Exception:
        payload = {}
    if isinstance(payload, dict):
        response_model = str(payload.get("model") or "").strip() or None

    if response.status_code == 200:
        notes.insert(0, "Provider-specific completion probe succeeded through VAULT LiteLLM.")
        return {
            "provider_id": provider_id,
            "status": "observed",
            "alias": alias,
            "requested_model": selected_model,
            "response_model": response_model or selected_model,
            "matched_by": matched_by,
            "http_status": response.status_code,
            "error_snippet": None,
            "proof_kind": "litellm_model_completion",
            "observed_at": utc_now(),
            "source": "vault-litellm-live-probe",
            "request_surface": request_surface,
            "notes": notes,
        }

    error_snippet = _short_error(response)
    notes.insert(0, f"Probe failed for requested model `{selected_model}`.")
    return {
        "provider_id": provider_id,
        "status": classify_probe_failure(response.status_code, error_snippet),
        "alias": alias,
        "requested_model": selected_model,
        "response_model": response_model,
        "matched_by": matched_by,
        "http_status": response.status_code,
        "error_snippet": error_snippet,
        "proof_kind": "litellm_model_completion",
        "observed_at": utc_now(),
        "source": "vault-litellm-live-probe",
        "request_surface": request_surface,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe VAULT LiteLLM provider-specific usage evidence.")
    parser.add_argument("--provider-id", action="append", default=[], help="Provider id to probe; can be repeated.")
    parser.add_argument(
        "--all-vault-proxy",
        action="store_true",
        help="Probe every provider in provider-catalog.json that uses the vault_litellm_proxy evidence contract.",
    )
    parser.add_argument("--write", type=Path, default=PROVIDER_USAGE_EVIDENCE_PATH)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--note", action="append", default=[], help="Optional note to attach to every capture.")
    parser.add_argument("--dry-run", action="store_true", help="Print captures without writing them.")
    args = parser.parse_args()

    provider_ids = [str(provider_id).strip() for provider_id in args.provider_id if str(provider_id).strip()]
    if args.all_vault_proxy:
        provider_ids.extend(iter_vault_proxy_provider_ids())
    provider_ids = sorted(set(provider_ids))
    if not provider_ids:
        raise SystemExit("No provider ids selected. Use --provider-id or --all-vault-proxy.")

    api_key = resolve_litellm_api_key()
    if not api_key:
        raise SystemExit("No LiteLLM API key available in ATHANOR_LITELLM_API_KEY, LITELLM_API_KEY, or LITELLM_MASTER_KEY.")

    base_url = litellm_base_url()
    captures: list[dict[str, object]] = []
    with httpx.Client(timeout=args.timeout_seconds) as client:
        served_models = list_served_models(client=client, base_url=base_url, api_key=api_key)
        for provider_id in provider_ids:
            capture = _probe_provider(
                provider_id,
                client=client,
                api_key=api_key,
                base_url=base_url,
                served_models=served_models,
                extra_notes=[str(note).strip() for note in args.note if str(note).strip()],
            )
            captures.append(capture)
            if not args.dry_run:
                append_capture(capture, path=args.write)
            print(json.dumps(capture, indent=2, sort_keys=True))

    statuses = {str(capture.get("status") or "") for capture in captures}
    if statuses <= {"observed", "verified"}:
        print("All selected provider probes were observed successfully.")
    else:
        print(f"Recorded mixed probe statuses: {sorted(statuses)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
