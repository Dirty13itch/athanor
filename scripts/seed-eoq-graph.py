#!/usr/bin/env python3
"""Seed Neo4j with Empire of Broken Queens — 21 Council Queens.

Creates Character nodes with personality vectors, inter-queen RELATIONSHIP
edges by archetype affinity, and Scene nodes. Idempotent via MERGE.

Usage:
    python3 scripts/seed-eoq-graph.py [--dry-run]

Options:
    --dry-run   Print Cypher statements without executing
    -h, --help  Show this help
"""

import argparse
import base64
import json
import os
import sys
import urllib.request

NEO4J_BASE_URL = (
    os.environ.get("ATHANOR_NEO4J_URL")
    or os.environ.get("NEO4J_URL")
    or "http://192.168.1.203:7474"
).rstrip("/")
NEO4J_URL = f"{NEO4J_BASE_URL}/db/neo4j/tx/commit"
NEO4J_USER = os.environ.get("ATHANOR_NEO4J_USER") or os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("ATHANOR_NEO4J_PASSWORD") or os.environ.get("NEO4J_PASSWORD", "")

# ---------------------------------------------------------------------------
# The 21 Council Queens (extracted from projects/eoq/src/data/queens.ts)
# ---------------------------------------------------------------------------

CHARACTERS = [
    {"name": "Emilie Ekstrom", "title": "The Ice Heiress", "archetype": "ice", "resistance": 90, "corruption": 5, "performer_reference": "Emilie Ekstrom", "breaking_stage": "defiant", "dominance": 0.7, "warmth": 0.3, "cunning": 0.8, "loyalty": 0.8, "cruelty": 0.2, "sensuality": 0.6, "humor": 0.3, "ambition": 0.9},
    {"name": "Jordan Night", "title": "The Nachtblume", "archetype": "fire", "resistance": 60, "corruption": 25, "performer_reference": "Jordan Night", "breaking_stage": "defiant", "dominance": 0.6, "warmth": 0.4, "cunning": 0.7, "loyalty": 0.3, "cruelty": 0.5, "sensuality": 0.85, "humor": 0.4, "ambition": 0.7},
    {"name": "Alanah Rae", "title": "The Plastic Doll", "archetype": "seductress", "resistance": 55, "corruption": 20, "performer_reference": "Alanah Rae", "breaking_stage": "defiant", "dominance": 0.3, "warmth": 0.6, "cunning": 0.4, "loyalty": 0.7, "cruelty": 0.1, "sensuality": 0.9, "humor": 0.5, "ambition": 0.4},
    {"name": "Nikki Benz", "title": "The Royal Brat", "archetype": "defiant", "resistance": 85, "corruption": 10, "performer_reference": "Nikki Benz", "breaking_stage": "defiant", "dominance": 0.85, "warmth": 0.25, "cunning": 0.7, "loyalty": 0.5, "cruelty": 0.6, "sensuality": 0.75, "humor": 0.35, "ambition": 0.95},
    {"name": "Chloe Lamour", "title": "The Surgeon's Shame", "archetype": "shadow", "resistance": 45, "corruption": 30, "performer_reference": "Chloe Lamour", "breaking_stage": "struggling", "dominance": 0.35, "warmth": 0.5, "cunning": 0.3, "loyalty": 0.6, "cruelty": 0.1, "sensuality": 0.95, "humor": 0.2, "ambition": 0.3},
    {"name": "Nicolette Shea", "title": "The Tower", "archetype": "sun", "resistance": 75, "corruption": 15, "performer_reference": "Nicolette Shea", "breaking_stage": "defiant", "dominance": 0.8, "warmth": 0.35, "cunning": 0.6, "loyalty": 0.4, "cruelty": 0.3, "sensuality": 0.85, "humor": 0.25, "ambition": 0.85},
    {"name": "Peta Jensen", "title": "The Nordic Fire", "archetype": "priestess", "resistance": 80, "corruption": 10, "performer_reference": "Peta Jensen", "breaking_stage": "defiant", "dominance": 0.65, "warmth": 0.5, "cunning": 0.5, "loyalty": 0.7, "cruelty": 0.15, "sensuality": 0.8, "humor": 0.3, "ambition": 0.6},
    {"name": "Sandee Westgate", "title": "The Exotic Flame", "archetype": "seductress", "resistance": 50, "corruption": 25, "performer_reference": "Sandee Westgate", "breaking_stage": "struggling", "dominance": 0.4, "warmth": 0.55, "cunning": 0.5, "loyalty": 0.45, "cruelty": 0.2, "sensuality": 0.9, "humor": 0.45, "ambition": 0.5},
    {"name": "Marisol Yotta", "title": "The Cam Queen", "archetype": "fire", "resistance": 40, "corruption": 35, "performer_reference": "Marisol Yotta", "breaking_stage": "struggling", "dominance": 0.5, "warmth": 0.45, "cunning": 0.6, "loyalty": 0.3, "cruelty": 0.25, "sensuality": 0.95, "humor": 0.5, "ambition": 0.65},
    {"name": "Trina Michaels", "title": "The Pain Queen", "archetype": "defiant", "resistance": 70, "corruption": 20, "performer_reference": "Trina Michaels", "breaking_stage": "defiant", "dominance": 0.55, "warmth": 0.3, "cunning": 0.4, "loyalty": 0.5, "cruelty": 0.4, "sensuality": 0.7, "humor": 0.35, "ambition": 0.5},
    {"name": "Nikki Sexx", "title": "The Throat GOAT", "archetype": "warrior", "resistance": 65, "corruption": 15, "performer_reference": "Nikki Sexx", "breaking_stage": "defiant", "dominance": 0.45, "warmth": 0.4, "cunning": 0.35, "loyalty": 0.6, "cruelty": 0.15, "sensuality": 0.85, "humor": 0.5, "ambition": 0.45},
    {"name": "Madison Ivy", "title": "The Tiny Destroyer", "archetype": "innocent", "resistance": 75, "corruption": 10, "performer_reference": "Madison Ivy", "breaking_stage": "defiant", "dominance": 0.7, "warmth": 0.35, "cunning": 0.6, "loyalty": 0.55, "cruelty": 0.3, "sensuality": 0.9, "humor": 0.4, "ambition": 0.8},
    {"name": "Amy Anderssen", "title": "The Monster Queen", "archetype": "sun", "resistance": 50, "corruption": 25, "performer_reference": "Amy Anderssen", "breaking_stage": "struggling", "dominance": 0.4, "warmth": 0.6, "cunning": 0.3, "loyalty": 0.7, "cruelty": 0.1, "sensuality": 0.95, "humor": 0.55, "ambition": 0.35},
    {"name": "Puma Swede", "title": "The Ex-Domme", "archetype": "warrior", "resistance": 80, "corruption": 5, "performer_reference": "Puma Swede", "breaking_stage": "defiant", "dominance": 0.9, "warmth": 0.2, "cunning": 0.5, "loyalty": 0.6, "cruelty": 0.5, "sensuality": 0.7, "humor": 0.3, "ambition": 0.7},
    {"name": "Ava Addams", "title": "The MILF Boss", "archetype": "seductress", "resistance": 65, "corruption": 15, "performer_reference": "Ava Addams", "breaking_stage": "defiant", "dominance": 0.6, "warmth": 0.5, "cunning": 0.7, "loyalty": 0.55, "cruelty": 0.2, "sensuality": 0.9, "humor": 0.4, "ambition": 0.6},
    {"name": "Brooklyn Chase", "title": "The Good Girl Gone", "archetype": "innocent", "resistance": 55, "corruption": 20, "performer_reference": "Brooklyn Chase", "breaking_stage": "defiant", "dominance": 0.3, "warmth": 0.65, "cunning": 0.35, "loyalty": 0.7, "cruelty": 0.1, "sensuality": 0.8, "humor": 0.5, "ambition": 0.4},
    {"name": "Esperanza Gomez", "title": "The Latina Fire", "archetype": "fire", "resistance": 60, "corruption": 20, "performer_reference": "Esperanza Gomez", "breaking_stage": "defiant", "dominance": 0.55, "warmth": 0.5, "cunning": 0.5, "loyalty": 0.5, "cruelty": 0.2, "sensuality": 0.9, "humor": 0.45, "ambition": 0.55},
    {"name": "Savannah Bond", "title": "The Aussie Bimbo", "archetype": "sun", "resistance": 45, "corruption": 30, "performer_reference": "Savannah Bond", "breaking_stage": "struggling", "dominance": 0.35, "warmth": 0.65, "cunning": 0.3, "loyalty": 0.6, "cruelty": 0.1, "sensuality": 0.95, "humor": 0.6, "ambition": 0.4},
    {"name": "Shyla Stylez", "title": "The Original Doll", "archetype": "seductress", "resistance": 55, "corruption": 20, "performer_reference": "Shyla Stylez", "breaking_stage": "defiant", "dominance": 0.5, "warmth": 0.45, "cunning": 0.55, "loyalty": 0.5, "cruelty": 0.2, "sensuality": 0.85, "humor": 0.4, "ambition": 0.55},
    {"name": "Brianna Banks", "title": "The Golden Era", "archetype": "seductress", "resistance": 60, "corruption": 15, "performer_reference": "Brianna Banks", "breaking_stage": "defiant", "dominance": 0.55, "warmth": 0.4, "cunning": 0.65, "loyalty": 0.45, "cruelty": 0.25, "sensuality": 0.85, "humor": 0.35, "ambition": 0.6},
    {"name": "Clanddi Jinkcebo", "title": "The French Fetish Goddess", "archetype": "shadow", "resistance": 70, "corruption": 10, "performer_reference": "Clanddi Jinkcebo", "breaking_stage": "defiant", "dominance": 0.75, "warmth": 0.3, "cunning": 0.7, "loyalty": 0.5, "cruelty": 0.45, "sensuality": 0.9, "humor": 0.4, "ambition": 0.6},
]

# ---------------------------------------------------------------------------
# Inter-queen relationships generated from archetype affinities
# ---------------------------------------------------------------------------

ARCHETYPE_CONFLICTS = {
    ("ice", "fire"), ("fire", "ice"),
    ("defiant", "innocent"), ("innocent", "defiant"),
    ("warrior", "shadow"), ("shadow", "warrior"),
    ("sun", "shadow"), ("shadow", "sun"),
}

ARCHETYPE_ALLIANCES = {
    ("seductress", "seductress"), ("fire", "fire"),
    ("warrior", "warrior"), ("sun", "sun"),
    ("seductress", "innocent"), ("innocent", "seductress"),
    ("priestess", "ice"), ("ice", "priestess"),
}


def generate_relationships():
    """Generate inter-queen relationships based on archetype affinity."""
    rels = []
    for i, q1 in enumerate(CHARACTERS):
        for q2 in CHARACTERS[i + 1:]:
            pair = (q1["archetype"], q2["archetype"])
            if pair in ARCHETYPE_CONFLICTS:
                rels.append({
                    "from": q1["name"], "to": q2["name"],
                    "type": "rival", "intensity": 0.7, "trust": -0.5,
                    "description": f"{q1['title']} and {q2['title']} — opposing archetypes create natural tension.",
                })
                rels.append({
                    "from": q2["name"], "to": q1["name"],
                    "type": "rival", "intensity": 0.65, "trust": -0.45,
                    "description": f"{q2['title']} and {q1['title']} — the friction runs both ways.",
                })
            elif pair in ARCHETYPE_ALLIANCES:
                rels.append({
                    "from": q1["name"], "to": q2["name"],
                    "type": "ally", "intensity": 0.6, "trust": 0.3,
                    "description": f"{q1['title']} and {q2['title']} — shared archetype affinity.",
                })
                rels.append({
                    "from": q2["name"], "to": q1["name"],
                    "type": "ally", "intensity": 0.55, "trust": 0.25,
                    "description": f"{q2['title']} and {q1['title']} — kindred spirits in the court.",
                })
    return rels


RELATIONSHIPS = generate_relationships()

# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

SCENES = [
    {
        "name": "The Shattered Throne Room",
        "description": "Once the seat of absolute power, now a ruin of cracked marble and fallen banners. The throne itself is split in two, each half claimed by a different faction.",
        "visual_prompt": "Dark fantasy throne room, cracked marble floor, shattered dome ceiling, moonlight streaming through, torn banners, broken throne, atmospheric fog, cinematic lighting, 8k",
        "characters": ["Emilie Ekstrom", "Nikki Benz", "Puma Swede"],
    },
    {
        "name": "The Garden of Whispers",
        "description": "A courtyard garden overgrown with nightshade and black roses. Hidden alcoves and vine-draped passages make it the court's preferred venue for schemes.",
        "visual_prompt": "Dark fantasy garden, nightshade and black roses, bioluminescent fungi, vine-covered stone archways, moonlit, hidden alcoves, cinematic lighting, 8k",
        "characters": ["Chloe Lamour", "Clanddi Jinkcebo", "Ava Addams"],
    },
    {
        "name": "The Blood Court",
        "description": "A circular amphitheater carved from obsidian, where disputes are settled by trial of blood. The sand floor is permanently stained crimson.",
        "visual_prompt": "Dark fantasy arena, obsidian amphitheater, blood-stained sand floor, iron braziers with flames, harsh shadows, cinematic lighting, 8k",
        "characters": ["Trina Michaels", "Nikki Sexx", "Madison Ivy", "Peta Jensen"],
    },
    {
        "name": "The Velvet Salon",
        "description": "A dimly lit chamber of silk curtains and flickering candlelight. The air is heavy with perfume and unspoken promises. Power is traded here in whispers.",
        "visual_prompt": "Dark fantasy salon, silk curtains, candlelight, opulent furniture, dark wood, perfumed atmosphere, intimate shadows, cinematic lighting, 8k",
        "characters": ["Alanah Rae", "Sandee Westgate", "Brianna Banks", "Shyla Stylez"],
    },
    {
        "name": "The Tower of Glass",
        "description": "Nicolette Shea's domain — a tower of crystalline walls that amplify sunlight by day and reflect moonlight by night.",
        "visual_prompt": "Fantasy crystal tower interior, glass walls refracting light, panoramic views, throne-like chair, prism rainbows, ethereal atmosphere, cinematic lighting, 8k",
        "characters": ["Nicolette Shea", "Amy Anderssen", "Savannah Bond"],
    },
]

# ---------------------------------------------------------------------------
# Neo4j HTTP helper
# ---------------------------------------------------------------------------


def neo4j_query(statements: list[dict], dry_run: bool = False) -> dict:
    """Execute Cypher statements against Neo4j HTTP transactional endpoint."""
    if dry_run:
        for s in statements:
            stmt = s["statement"]
            print(f"  CYPHER: {stmt[:140]}...", file=sys.stderr)
        return {"results": [], "errors": []}

    if not NEO4J_PASS:
        raise RuntimeError("Set ATHANOR_NEO4J_PASSWORD or NEO4J_PASSWORD before writing to Neo4j.")

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
            ch.performer_reference = $performer_reference,
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
        description="Seed Neo4j with EoBQ character relationship graph — 21 Council Queens."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print Cypher statements without executing",
    )
    args = parser.parse_args()

    print("Seeding EoBQ character graph (21 queens)...", file=sys.stderr)

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
