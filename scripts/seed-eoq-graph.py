#!/usr/bin/env python3
"""Seed Neo4j with Empire of Broken Queens character graph.

Creates Character nodes, Scene nodes, inter-character RELATIONSHIP edges,
and APPEARS_IN edges. Idempotent via MERGE.

Usage:
    python3 scripts/seed-eoq-graph.py [--dry-run]

Options:
    --dry-run   Print Cypher statements without executing
    -h, --help  Show this help
"""

import argparse
import base64
import json
import sys
import urllib.request

NEO4J_URL = "http://192.168.1.203:7474/db/neo4j/tx/commit"
NEO4J_USER = "neo4j"
NEO4J_PASS = "athanor2026"

# ---------------------------------------------------------------------------
# Character definitions
# ---------------------------------------------------------------------------

CHARACTERS = [
    {
        "name": "Isolde",
        "title": "The Deposed Queen",
        "archetype": "ice",
        "breaking_stage": "defiant",
        "resistance": 90,
        "corruption": 5,
        "visual_description": (
            "Regal woman in her 30s, sharp angular features, dark auburn hair "
            "in elaborate braids threaded with thin gold chains, pale porcelain "
            "skin, ice-blue eyes. Wears a fitted black and gold gown with high "
            "structured collar. A thin scar runs from her left ear to her jaw."
        ),
        # PersonalityVector
        "dominance": 0.9,
        "warmth": 0.2,
        "cunning": 0.7,
        "loyalty": 0.6,
        "cruelty": 0.4,
        "sensuality": 0.5,
        "humor": 0.15,
        "ambition": 0.95,
    },
    {
        "name": "Seraphine",
        "title": "The Oracle of Ashes",
        "archetype": "sorceress",
        "breaking_stage": "defiant",
        "resistance": 85,
        "corruption": 10,
        "visual_description": (
            "Young woman with an ethereal, fragile beauty. Silver-white hair "
            "falling past her shoulders, violet eyes with an otherworldly glow. "
            "Wears tattered white and lavender robes. Faint magical sigils trace "
            "patterns on her skin. Dark circles under her eyes from sleepless visions."
        ),
        "dominance": 0.4,
        "warmth": 0.5,
        "cunning": 0.8,
        "loyalty": 0.3,
        "cruelty": 0.3,
        "sensuality": 0.6,
        "humor": 0.1,
        "ambition": 0.7,
    },
    {
        "name": "Valeria",
        "title": "The Iron Marshal",
        "archetype": "warrior",
        "breaking_stage": "defiant",
        "resistance": 95,
        "corruption": 0,
        "visual_description": (
            "Muscular woman in her late 20s, sun-bronzed skin, close-cropped "
            "dark hair with a streak of premature grey. Strong jaw, hawkish "
            "nose, amber eyes. Wears battered steel plate armor over chainmail. "
            "Multiple battle scars on her arms and face."
        ),
        "dominance": 0.85,
        "warmth": 0.35,
        "cunning": 0.4,
        "loyalty": 0.8,
        "cruelty": 0.2,
        "sensuality": 0.3,
        "humor": 0.25,
        "ambition": 0.6,
    },
    {
        "name": "Lilith",
        "title": "The Crimson Whisper",
        "archetype": "seductress",
        "breaking_stage": "struggling",
        "resistance": 70,
        "corruption": 35,
        "visual_description": (
            "Strikingly beautiful woman with an unsettling edge. Long black hair, "
            "blood-red lips, dark eyes with flecks of gold. Wears a deep crimson "
            "dress that seems to shift between liquid and fabric. Pale skin with "
            "a faint luminescence."
        ),
        "dominance": 0.7,
        "warmth": 0.15,
        "cunning": 0.95,
        "loyalty": 0.1,
        "cruelty": 0.85,
        "sensuality": 0.9,
        "humor": 0.3,
        "ambition": 0.8,
    },
    {
        "name": "Mireille",
        "title": "The Fox of Thornfield",
        "archetype": "shadow",
        "breaking_stage": "defiant",
        "resistance": 80,
        "corruption": 15,
        "visual_description": (
            "Petite woman with sharp, fox-like features. Copper-red curls, "
            "freckled skin, bright green eyes that miss nothing. Wears practical "
            "dark leather with hidden pockets. Multiple rings and a thin dagger "
            "at her belt."
        ),
        "dominance": 0.5,
        "warmth": 0.4,
        "cunning": 0.9,
        "loyalty": 0.45,
        "cruelty": 0.35,
        "sensuality": 0.55,
        "humor": 0.6,
        "ambition": 0.5,
    },
]

# ---------------------------------------------------------------------------
# Inter-character relationships (bidirectional, stored as two directed edges)
# ---------------------------------------------------------------------------

RELATIONSHIPS = [
    # Isolde <-> Seraphine: rivals for the throne, mutual respect but deep distrust
    {
        "from": "Isolde", "to": "Seraphine",
        "type": "rival", "intensity": 0.85, "trust": -0.6,
        "description": "Rivals for the shattered throne. Isolde sees Seraphine's visions as a threat to her legitimacy. Mutual grudging respect masked by cold hostility.",
    },
    {
        "from": "Seraphine", "to": "Isolde",
        "type": "rival", "intensity": 0.8, "trust": -0.5,
        "description": "Seraphine's prophecies name Isolde's fall, yet she fears the queen's iron will. Respects the crown but not the woman wearing it.",
    },
    # Isolde <-> Valeria: former allies, Valeria betrayed Isolde
    {
        "from": "Isolde", "to": "Valeria",
        "type": "nemesis", "intensity": 0.95, "trust": -0.9,
        "description": "Once her most trusted commander, Valeria's betrayal shattered Isolde's ability to trust anyone. The wound festers — hatred entwined with grief.",
    },
    {
        "from": "Valeria", "to": "Isolde",
        "type": "nemesis", "intensity": 0.7, "trust": -0.4,
        "description": "Valeria believes her betrayal was necessary — Isolde's reign was heading toward tyranny. Guilt mixes with conviction. She avoids Isolde's gaze.",
    },
    # Lilith <-> Mireille: dark mentor/student dynamic
    {
        "from": "Lilith", "to": "Mireille",
        "type": "servant", "intensity": 0.75, "trust": 0.3,
        "description": "Lilith sees Mireille as a useful protégé — sharp, corruptible, eager. She drips poison into the girl's ear, shaping her into a weapon.",
    },
    {
        "from": "Mireille", "to": "Lilith",
        "type": "ally", "intensity": 0.65, "trust": 0.15,
        "description": "Mireille knows Lilith is using her but craves the power Lilith offers. The fox learns from the serpent, waiting for the right moment to bite back.",
    },
    # Seraphine <-> Lilith: uneasy alliance against Isolde
    {
        "from": "Seraphine", "to": "Lilith",
        "type": "ally", "intensity": 0.6, "trust": -0.2,
        "description": "Seraphine's visions show Lilith as both ally and destroyer. Their pact against Isolde is pragmatic and fragile — each watching for the knife.",
    },
    {
        "from": "Lilith", "to": "Seraphine",
        "type": "ally", "intensity": 0.55, "trust": -0.3,
        "description": "Lilith considers Seraphine's power useful but her morality inconvenient. She whispers alliance while planning contingencies.",
    },
    # Valeria <-> Mireille: mutual contempt
    {
        "from": "Valeria", "to": "Mireille",
        "type": "rival", "intensity": 0.5, "trust": -0.7,
        "description": "Valeria despises everything Mireille represents — subterfuge, manipulation, the coward's path. She sees Lilith's shadow behind those green eyes.",
    },
    {
        "from": "Mireille", "to": "Valeria",
        "type": "rival", "intensity": 0.45, "trust": -0.65,
        "description": "Mireille finds Valeria's blunt honor laughable, a relic of an age that's already dead. But she respects the sword arm and keeps her distance.",
    },
]

# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

SCENES = [
    {
        "name": "The Shattered Throne Room",
        "description": (
            "Once the seat of absolute power, now a ruin of cracked marble and "
            "fallen banners. The throne itself is split in two, each half claimed "
            "by a different faction. Moonlight pours through the shattered dome."
        ),
        "visual_prompt": (
            "Dark fantasy throne room, cracked marble floor, shattered dome ceiling, "
            "moonlight streaming through, torn banners, broken throne, atmospheric fog, "
            "cinematic lighting, 8k"
        ),
        "characters": ["Isolde", "Seraphine", "Valeria"],
    },
    {
        "name": "The Garden of Whispers",
        "description": (
            "A courtyard garden overgrown with nightshade and black roses. Hidden "
            "alcoves and vine-draped passages make it the court's preferred venue "
            "for schemes and secret rendezvous. Soft bioluminescent fungi pulse along the walls."
        ),
        "visual_prompt": (
            "Dark fantasy garden, nightshade and black roses, bioluminescent fungi, "
            "vine-covered stone archways, moonlit, hidden alcoves, atmospheric, "
            "cinematic lighting, 8k"
        ),
        "characters": ["Lilith", "Mireille", "Seraphine"],
    },
    {
        "name": "The Blood Court",
        "description": (
            "A circular amphitheater carved from obsidian, where disputes are settled "
            "by trial of blood. The sand floor is permanently stained crimson. Iron "
            "braziers ring the perimeter, casting harsh dancing shadows."
        ),
        "visual_prompt": (
            "Dark fantasy arena, obsidian amphitheater, blood-stained sand floor, "
            "iron braziers with flames, harsh shadows, foreboding atmosphere, "
            "cinematic lighting, 8k"
        ),
        "characters": ["Valeria", "Isolde", "Lilith", "Mireille"],
    },
]

# ---------------------------------------------------------------------------
# Neo4j HTTP helper (matches graph-bookmarks.py pattern)
# ---------------------------------------------------------------------------


def neo4j_query(statements: list[dict], dry_run: bool = False) -> dict:
    """Execute Cypher statements against Neo4j HTTP transactional endpoint."""
    if dry_run:
        for s in statements:
            stmt = s["statement"]
            print(f"  CYPHER: {stmt[:140]}...", file=sys.stderr)
        return {"results": [], "errors": []}

    payload = json.dumps({"statements": statements}).encode()
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()
    req = urllib.request.Request(
        NEO4J_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if result.get("errors"):
        for err in result["errors"]:
            print(f"  ERROR: {err['message']}", file=sys.stderr)
        sys.exit(1)
    return result


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------


def seed_characters(dry_run: bool = False) -> int:
    """Create Character nodes with personality vectors."""
    statements = []
    for c in CHARACTERS:
        cypher = """
        MERGE (ch:Character {name: $name})
        SET ch.title = $title,
            ch.archetype = $archetype,
            ch.breaking_stage = $breaking_stage,
            ch.resistance = $resistance,
            ch.corruption = $corruption,
            ch.visual_description = $visual_description,
            ch.dominance = $dominance,
            ch.warmth = $warmth,
            ch.cunning = $cunning,
            ch.loyalty = $loyalty,
            ch.cruelty = $cruelty,
            ch.sensuality = $sensuality,
            ch.humor = $humor,
            ch.ambition = $ambition,
            ch.domain = 'eoq',
            ch.updated_at = datetime()
        """
        statements.append({"statement": cypher, "parameters": c})
    neo4j_query(statements, dry_run=dry_run)
    return len(statements)


def seed_relationships(dry_run: bool = False) -> int:
    """Create directed RELATIONSHIP edges between characters."""
    statements = []
    for r in RELATIONSHIPS:
        cypher = """
        MATCH (a:Character {name: $from})
        MATCH (b:Character {name: $to})
        MERGE (a)-[rel:RELATIONSHIP {type: $type}]->(b)
        SET rel.intensity = $intensity,
            rel.trust = $trust,
            rel.description = $description,
            rel.domain = 'eoq',
            rel.updated_at = datetime()
        """
        statements.append({"statement": cypher, "parameters": r})
    neo4j_query(statements, dry_run=dry_run)
    return len(statements)


def seed_scenes(dry_run: bool = False) -> int:
    """Create Scene nodes and APPEARS_IN edges."""
    statements = []
    for s in SCENES:
        # Create the scene
        cypher_scene = """
        MERGE (sc:Scene {name: $name})
        SET sc.description = $description,
            sc.visual_prompt = $visual_prompt,
            sc.domain = 'eoq',
            sc.updated_at = datetime()
        """
        statements.append({
            "statement": cypher_scene,
            "parameters": {
                "name": s["name"],
                "description": s["description"],
                "visual_prompt": s["visual_prompt"],
            },
        })
        # APPEARS_IN edges
        for char_name in s["characters"]:
            cypher_edge = """
            MATCH (ch:Character {name: $char_name})
            MATCH (sc:Scene {name: $scene_name})
            MERGE (ch)-[:APPEARS_IN]->(sc)
            """
            statements.append({
                "statement": cypher_edge,
                "parameters": {"char_name": char_name, "scene_name": s["name"]},
            })
    neo4j_query(statements, dry_run=dry_run)
    return len(statements)


def verify_graph(dry_run: bool = False) -> None:
    """Print summary counts of seeded graph elements."""
    if dry_run:
        print("  [dry-run] Skipping verification", file=sys.stderr)
        return

    counts = [
        ("Characters", "MATCH (c:Character {domain: 'eoq'}) RETURN count(c) AS n"),
        ("Scenes", "MATCH (s:Scene {domain: 'eoq'}) RETURN count(s) AS n"),
        ("RELATIONSHIP edges", "MATCH ()-[r:RELATIONSHIP {domain: 'eoq'}]->() RETURN count(r) AS n"),
        ("APPEARS_IN edges", "MATCH (:Character)-[a:APPEARS_IN]->(:Scene {domain: 'eoq'}) RETURN count(a) AS n"),
    ]
    for label, cypher in counts:
        result = neo4j_query(
            [{"statement": cypher, "resultDataContents": ["row"]}],
        )
        n = result["results"][0]["data"][0]["row"][0]
        print(f"  {label}: {n}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Neo4j with EoBQ character relationship graph."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print Cypher statements without executing",
    )
    args = parser.parse_args()

    print("Seeding EoBQ character graph...", file=sys.stderr)

    n_chars = seed_characters(dry_run=args.dry_run)
    print(f"  Characters: {n_chars} merged", file=sys.stderr)

    n_rels = seed_relationships(dry_run=args.dry_run)
    print(f"  Relationships: {n_rels} merged", file=sys.stderr)

    n_scenes = seed_scenes(dry_run=args.dry_run)
    print(f"  Scenes + APPEARS_IN: {n_scenes} merged", file=sys.stderr)

    print("Verifying...", file=sys.stderr)
    verify_graph(dry_run=args.dry_run)

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
