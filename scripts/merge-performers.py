#!/usr/bin/env python3
"""Enrich performers.json by parsing waist/hip from bust_waist_hip field
and backfilling career_start from available data.

This script operates on the existing performers.json on VAULT and enriches
records in-place. It does NOT require source xlsx files - it works with
data already present in the JSON.

Enrichments:
  1. Parse waist/hip from bust_waist_hip (e.g. "36DD-28-36" -> waist=28, hip=36)
  2. Normalize career_start values (strip .0, handle ranges)
  3. Summary stats

Usage:
    python3 scripts/merge-performers.py
    python3 scripts/merge-performers.py --dry-run
    python3 scripts/merge-performers.py --input /path/to/performers.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from copy import deepcopy


DEFAULT_PATH = Path("/mnt/vault/data/performers.json")


def parse_bwh(bwh: str) -> tuple[str, str, str]:
    """Parse bust-waist-hip string into components.
    
    Handles formats like:
      36DD-28-36
      32DDD-24-34
      34D-26-36
      36-28-36
      34DD - 26 - 35
    
    Returns (bust, waist, hip) as strings, empty string if unparseable.
    """
    if not bwh or not bwh.strip():
        return ("", "", "")

    bwh = bwh.strip()

    # Pattern: number(+letters) - number - number
    # The bust part can have cup size letters attached
    m = re.match(
        r"^(\d{2,3}[A-Za-z]*)\s*[-/]\s*(\d{2,3})\s*[-/]\s*(\d{2,3})$",
        bwh
    )
    if m:
        return (m.group(1), m.group(2), m.group(3))

    return ("", "", "")


def normalize_career_start(val) -> str:
    """Normalize career_start field.
    
    Handles: "2010.0" -> "2010", "2008-2015" -> "2008", int/float -> str
    """
    if val is None or val == "" or val == 0:
        return ""
    
    s = str(val).strip()
    if not s:
        return ""

    # Handle float-like strings: "2010.0" -> "2010"
    try:
        f = float(s)
        if 1960 <= f <= 2030:
            return str(int(f))
    except (ValueError, TypeError):
        pass

    # Handle ranges: "2008-2015" -> "2008"
    m = re.match(r"^(\d{4})\s*[-–]\s*\d{4}$", s)
    if m:
        return m.group(1)

    # Handle plain year
    m = re.match(r"^(\d{4})$", s)
    if m:
        return m.group(1)

    return s


def enrich_performers(performers: list[dict], dry_run: bool = False) -> dict:
    """Enrich performer records. Returns stats dict."""
    stats = {
        "total": len(performers),
        "waist_before": 0,
        "waist_after": 0,
        "hip_before": 0,
        "hip_after": 0,
        "career_start_before": 0,
        "career_start_after": 0,
        "career_start_normalized": 0,
        "bwh_parsed": 0,
        "bwh_failed": [],
    }

    for p in performers:
        # Count before
        if p.get("waist"):
            stats["waist_before"] += 1
        if p.get("hip"):
            stats["hip_before"] += 1
        if p.get("career_start"):
            stats["career_start_before"] += 1

        # --- Parse waist/hip from bust_waist_hip ---
        bwh = p.get("bust_waist_hip", "")
        if bwh and (not p.get("waist") or not p.get("hip")):
            bust_parsed, waist_parsed, hip_parsed = parse_bwh(bwh)
            if waist_parsed and hip_parsed:
                if not p.get("waist"):
                    p["waist"] = waist_parsed
                if not p.get("hip"):
                    p["hip"] = hip_parsed
                # Also update bust if we have a better value with cup size
                if bust_parsed and not p.get("bust"):
                    p["bust"] = bust_parsed
                stats["bwh_parsed"] += 1
            else:
                stats["bwh_failed"].append((p.get("name", "?"), bwh))

        # --- Normalize career_start ---
        raw_cs = p.get("career_start", "")
        normalized = normalize_career_start(raw_cs)
        if normalized != raw_cs:
            p["career_start"] = normalized
            stats["career_start_normalized"] += 1

        # Count after
        if p.get("waist"):
            stats["waist_after"] += 1
        if p.get("hip"):
            stats["hip_after"] += 1
        if p.get("career_start"):
            stats["career_start_after"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Enrich performers.json with parsed measurements")
    parser.add_argument("--input", type=Path, default=DEFAULT_PATH,
                        help=f"Input performers.json (default: {DEFAULT_PATH})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing")
    args = parser.parse_args()

    path = args.input
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)

    print(f"Loading: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} performers")
    print()

    # Make a backup reference
    original = deepcopy(data)

    stats = enrich_performers(data, dry_run=args.dry_run)

    # Print report
    print("=" * 60)
    print("ENRICHMENT REPORT")
    print("=" * 60)
    print(f"  Total performers:         {stats['total']}")
    print()
    print(f"  Waist:   {stats['waist_before']:3d} -> {stats['waist_after']:3d}  "+
          f"(+{stats['waist_after'] - stats['waist_before']})")
    print(f"  Hip:     {stats['hip_before']:3d} -> {stats['hip_after']:3d}  "+
          f"(+{stats['hip_after'] - stats['hip_before']})")
    print(f"  Career:  {stats['career_start_before']:3d} -> {stats['career_start_after']:3d}  "+
          f"(+{stats['career_start_after'] - stats['career_start_before']})")
    print()
    print(f"  BWH strings parsed:       {stats['bwh_parsed']}")
    print(f"  Career_start normalized:  {stats['career_start_normalized']}")

    if stats["bwh_failed"]:
        print(f"\n  BWH parse failures ({len(stats['bwh_failed'])}):")
        for name, bwh in stats["bwh_failed"][:10]:
            print(f"    {name}: \"{bwh}\"")
        if len(stats["bwh_failed"]) > 10:
            print(f"    ... and {len(stats['bwh_failed']) - 10} more")

    # Show sample enriched records
    enriched = [p for p, o in zip(data, original)
                if p.get("waist") and not o.get("waist")]
    if enriched:
        print(f"\n  Sample enriched records:")
        for p in enriched[:5]:
            print(f"    {p['name']}: waist={p['waist']}, hip={p['hip']}, "+
                  f"bwh={p.get('bust_waist_hip','')}")

    if args.dry_run:
        print("\n  DRY RUN -- no changes written")
        return

    # Write back
    backup = path.with_suffix(".json.bak")
    print(f"\n  Backup: {backup}")
    backup.write_text(json.dumps(original, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Writing: {path}")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  Done!")


if __name__ == "__main__":
    main()
