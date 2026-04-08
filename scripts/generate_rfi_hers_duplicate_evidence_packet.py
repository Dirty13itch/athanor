from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TENANT_FAMILY_AUDIT_PATH = REPO_ROOT / "reports" / "reconciliation" / "tenant-family-audit-latest.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "rfi-hers-duplicate-evidence-packet-latest.json"
RFI_ROOT_ID = "rfi-hers-rater-assistant-root"
VARIANT_IDS = {
    "codexbuild-rfi-hers-rater-assistant",
    "codexbuild-rfi-hers-rater-assistant-safe",
    "codexbuild-rfi-hers-rater-assistant-v2",
}


def _load_rfi_family() -> dict[str, Any]:
    audit = json.loads(TENANT_FAMILY_AUDIT_PATH.read_text(encoding="utf-8"))
    for family in audit.get("families", []):
        if str(family.get("root_id") or "") == RFI_ROOT_ID:
            return dict(family)
    raise RuntimeError(f"Unable to find {RFI_ROOT_ID} in {TENANT_FAMILY_AUDIT_PATH}")


def _classify_artifact(path: str) -> str:
    if path == "tsconfig.tsbuildinfo":
        return "disposable"
    if path.startswith("data/") and ".sqlite" in path:
        return "preserve_archive_evidence"
    if path.startswith("drizzle/") and path.endswith(".sql"):
        return "preserve_archive_evidence"
    if path.startswith("src/features/"):
        return "superseded_by_root"
    return "unclassified"


def _variant_report(member: dict[str, Any], only_vs_root: list[str]) -> dict[str, Any]:
    preserved: list[str] = []
    superseded: list[str] = []
    disposable: list[str] = []
    unclassified: list[str] = []

    for path in only_vs_root:
        classification = _classify_artifact(path)
        if classification == "preserve_archive_evidence":
            preserved.append(path)
        elif classification == "superseded_by_root":
            superseded.append(path)
        elif classification == "disposable":
            disposable.append(path)
        else:
            unclassified.append(path)

    return {
        "id": str(member.get("id") or ""),
        "name": str(member.get("name") or ""),
        "path": str((member.get("metadata") or {}).get("path") or ""),
        "authority_status": str(member.get("authority_status") or ""),
        "review_status": str(member.get("review_status") or ""),
        "default_disposition": str(member.get("default_disposition") or ""),
        "preservation_status": str(member.get("preservation_status") or ""),
        "preserve_archive_evidence": preserved,
        "superseded_by_root": superseded,
        "disposable_artifacts": disposable,
        "unclassified_artifacts": unclassified,
        "notes": list(member.get("notes") or []),
        "next_step": "Retain only the preserved evidence artifacts; treat the variant itself as archive-only.",
    }


def main() -> int:
    family = _load_rfi_family()
    file_delta_summary = {
        str(item.get("id") or ""): list(item.get("only_vs_root") or [])
        for item in family.get("file_delta_summary", [])
        if isinstance(item, dict)
    }
    members = [dict(item) for item in family.get("members", []) if str(item.get("id") or "") in VARIANT_IDS]
    variant_ids = {str(item.get("id") or "") for item in members}
    if variant_ids != VARIANT_IDS:
        missing = sorted(VARIANT_IDS - variant_ids)
        raise RuntimeError(f"RFI duplicate-evidence packet missing variants: {', '.join(missing)}")

    variants = [
        _variant_report(member, file_delta_summary.get(str(member.get("id") or ""), []))
        for member in sorted(members, key=lambda item: str(item.get("id") or ""))
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "family_root_id": str(family.get("root_id") or ""),
        "family_root_name": str(family.get("root_name") or ""),
        "root_path": str((family.get("root_metadata") or {}).get("path") or ""),
        "root_dirty_file_count": int((family.get("root_metadata") or {}).get("dirty_file_count") or 0),
        "root_authority_status": str(family.get("root_authority_status") or ""),
        "root_review_status": str(family.get("root_review_status") or ""),
        "variant_count": len(variants),
        "variants": variants,
        "rules": [
            "Do not treat any C:/CodexBuild/rfi-hers-rater-assistant* tree as an authority candidate or replay lane.",
            "Preserve only the SQLite and drizzle artifacts listed under preserve_archive_evidence for each variant.",
            "Treat src/features/* deltas in the plain variant as superseded by the root workspace's current namespaced feature tree.",
            "Ignore disposable build residue such as tsconfig.tsbuildinfo when preserving archive evidence.",
        ],
        "completion_condition": [
            "The root workspace remains the only repo-backed authority candidate.",
            "Each duplicate variant is preserved only for its bounded evidence artifacts and no longer treated as a shadow product root.",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
