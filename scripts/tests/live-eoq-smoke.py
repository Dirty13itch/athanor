#!/usr/bin/env python3
"""Smoke-test the live EoBQ tenant with safe low-volume checks."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from typing import Any
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import NODES

DEFAULT_BASE_URL = f"http://{NODES['workshop']}:3002"

ROUTES = ["/", "/gallery", "/references"]


def build_live_character() -> dict[str, Any]:
    return {
        "id": "isolde",
        "name": "Isolde",
        "title": "The Usurper Queen",
        "archetype": "ice",
        "resistance": 84,
        "corruption": 8,
        "vulnerabilities": {"psychological": 0.6, "social": 0.8},
        "personality": {
            "dominance": 0.8,
            "warmth": 0.3,
            "cunning": 0.9,
            "loyalty": 0.4,
            "cruelty": 0.5,
            "sensuality": 0.7,
            "humor": 0.4,
            "ambition": 0.95,
        },
        "relationship": {
            "trust": 14,
            "affection": 7,
            "respect": 34,
            "desire": 10,
            "fear": 16,
            "memories": [],
        },
        "emotion": {"primary": "calculating", "intensity": 0.6},
        "emotionalProfile": {
            "fear": 15,
            "defiance": 80,
            "arousal": 14,
            "submission": 4,
            "despair": 8,
        },
        "speechStyle": "Measured and dangerous.",
        "visualDescription": "Fixture portrait.",
        "boundaries": ["Will not beg.", "Will not yield easily."],
    }


def build_live_world_state() -> dict[str, Any]:
    return {
        "currentScene": {
            "id": "courtyard",
            "name": "Courtyard",
            "description": "A moonlit courtyard framed by ruined stone.",
            "visualPrompt": "Moonlit courtyard, ruined stone arches, dark fantasy.",
            "presentCharacters": ["isolde"],
            "exits": [{"label": "Walk to the keep", "targetSceneId": "ashenmoor-keep"}],
        },
        "timeOfDay": "night",
        "day": 1,
        "plotFlags": {},
        "inventory": ["royal-seal"],
        "contentIntensity": 3,
    }


def fetch(base_url: str, path: str, method: str = "GET", payload: Any = None, timeout: int = 45):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, dict(response.headers), response.read()


def read_sse(base_url: str, path: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
    )
    events: list[dict[str, Any]] = []
    with urllib.request.urlopen(request, timeout=60) as response:
        buffer = ""
        while True:
            chunk = response.read(1024)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                data_lines = [line[5:].lstrip() for line in block.split("\n") if line.startswith("data:")]
                if not data_lines:
                    continue
                data = "\n".join(data_lines)
                if data == "[DONE]":
                    return events
                try:
                    parsed = json.loads(data)
                    if parsed.get("choices"):
                        delta = parsed["choices"][0].get("delta", {})
                        finish_reason = parsed["choices"][0].get("finish_reason")
                        if delta.get("content"):
                            events.append({"type": "assistant_delta"})
                        elif finish_reason:
                            events.append({"type": "done"})
                        else:
                            events.append({"type": "unknown"})
                    else:
                        events.append(parsed)
                except json.JSONDecodeError:
                    events.append({"type": "malformed", "raw": data})
                if any(event.get("type") in {"done", "error"} for event in events):
                    return events
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--exercise-generation", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    summary: dict[str, Any] = {}

    for path in ROUTES:
        try:
            status, _, body = fetch(args.base_url, path)
            if status != 200 or "<html" not in body.decode("utf-8", errors="replace").lower():
                failures.append(f"route {path} unexpected status/content: {status}")
            else:
                summary[path] = "ok"
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"route {path} failed: {exc}")

    try:
        _, _, body = fetch(args.base_url, "/api/references")
        references = json.loads(body.decode("utf-8"))
        if not isinstance(references, list) or not references:
            failures.append("references endpoint returned no items")
        else:
            summary["references"] = len(references)
            ref_id = references[0]["id"]
            status, _, detail_body = fetch(args.base_url, f"/api/references/{ref_id}")
            if status != 200:
                failures.append(f"reference detail {ref_id} returned {status}")
            else:
                detail = json.loads(detail_body.decode("utf-8"))
                summary["referenceDetail"] = detail.get("id", ref_id)
    except Exception as exc:  # pragma: no cover - live smoke only
        failures.append(f"references failed: {exc}")

    try:
        _, _, body = fetch(args.base_url, "/api/gallery?limit=3")
        gallery = json.loads(body.decode("utf-8"))
        if not isinstance(gallery, dict) or not isinstance(gallery.get("images"), list):
            failures.append("gallery endpoint returned unexpected shape")
        else:
            summary["gallery"] = len(gallery["images"])
    except Exception as exc:  # pragma: no cover - live smoke only
        failures.append(f"gallery failed: {exc}")

    common_payload = {
        "character": build_live_character(),
        "worldState": build_live_world_state(),
        "recentHistory": [{"speaker": "isolde", "text": "You return uninvited."}],
    }

    try:
        events = read_sse(
            args.base_url,
            "/api/chat",
            {
                **common_payload,
                "playerInput": "Respond with a single short line in character.",
            },
        )
        if not events or any(event.get("type") == "error" for event in events):
            failures.append(f"dialogue failed: {events}")
        else:
            summary["dialogue"] = [event.get("type", "unknown") for event in events[:6]]
    except Exception as exc:  # pragma: no cover - live smoke only
        failures.append(f"dialogue failed: {exc}")

    try:
        events = read_sse(args.base_url, "/api/narrate", common_payload)
        if not events or any(event.get("type") == "error" for event in events):
            failures.append(f"narrate failed: {events}")
        else:
            summary["narrate"] = [event.get("type", "unknown") for event in events[:6]]
    except Exception as exc:  # pragma: no cover - live smoke only
        failures.append(f"narrate failed: {exc}")

    try:
        last_exc: Exception | None = None
        choices = None
        for _ in range(2):
            try:
                _, _, body = fetch(
                    args.base_url,
                    "/api/choices",
                    method="POST",
                    payload=common_payload,
                    timeout=90,
                )
                choices = json.loads(body.decode("utf-8"))
                break
            except Exception as exc:  # pragma: no cover - live smoke only
                last_exc = exc

        if choices is None:
            raise last_exc or RuntimeError("choices request failed")
        if not isinstance(choices, dict) or not isinstance(choices.get("choices"), list):
            failures.append("choices endpoint returned unexpected shape")
        elif len(choices["choices"]) == 0:
            failures.append("choices endpoint returned no options")
        else:
            summary["choices"] = len(choices["choices"])
    except Exception as exc:  # pragma: no cover - live smoke only
        failures.append(f"choices failed: {exc}")

    if args.exercise_generation:
        try:
            _, _, body = fetch(
                args.base_url,
                "/api/generate",
                method="POST",
                payload={"prompt": "dark fantasy portrait", "type": "portrait"},
            )
            generated = json.loads(body.decode("utf-8"))
            if "imageUrl" not in generated:
                failures.append("generation endpoint returned no imageUrl")
            else:
                summary["generate"] = "ok"
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"generation failed: {exc}")

    print(json.dumps({"baseUrl": args.base_url, "summary": summary, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
