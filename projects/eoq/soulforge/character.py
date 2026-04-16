"""Character model for Empire of Broken Queens.

A CharacterCard is the fully-realized output of the SoulForge pipeline:
DNA + backstory + portrait + voice sample, ready for Ren'Py integration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from soulforge.dna import SexualPersonalityDNA, dna_to_description


class Gender(str, Enum):
    FEMALE = "female"
    MALE = "male"
    NONBINARY = "nonbinary"


class Archetype(str, Enum):
    """High-level character archetypes that influence backstory generation."""
    QUEEN = "queen"
    KNIGHT = "knight"
    COURTESAN = "courtesan"
    SORCERESS = "sorceress"
    ASSASSIN = "assassin"
    MERCHANT = "merchant"
    PRIESTESS = "priestess"
    REBEL = "rebel"
    NOBLE = "noble"
    OUTCAST = "outcast"


# Default voice mapping: archetype -> speaches voice ID.
DEFAULT_VOICES: Dict[str, str] = {
    "queen":      "af_bella",
    "knight":     "am_fenrir",
    "courtesan":  "af_jessica",
    "sorceress":  "af_kore",
    "assassin":   "af_nova",
    "merchant":   "am_eric",
    "priestess":  "bf_emma",
    "rebel":      "af_river",
    "noble":      "bf_isabella",
    "outcast":    "af_sky",
}


@dataclass
class CharacterCard:
    """A fully-realized EoBQ character."""

    # Identity.
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    title: str = ""  # e.g. "The Shattered Queen", "Blade of the Red Court"
    gender: Gender = Gender.FEMALE
    archetype: Archetype = Archetype.QUEEN
    age: int = 25

    # Personality DNA.
    dna: SexualPersonalityDNA = field(default_factory=SexualPersonalityDNA)

    # Generated content.
    backstory: str = ""
    personality_summary: str = ""
    appearance_description: str = ""

    # Asset paths (populated by SoulForge pipeline).
    portrait_path: Optional[str] = None
    voice_sample_path: Optional[str] = None
    voice_id: str = ""  # speaches voice ID

    # Metadata.
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    generation_seed: Optional[int] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.personality_summary and self.dna:
            self.personality_summary = dna_to_description(self.dna)
        if not self.voice_id:
            self.voice_id = DEFAULT_VOICES.get(self.archetype.value, "af_heart")

    def to_dict(self) -> Dict:
        """Serialize to dict for JSON storage."""
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "gender": self.gender.value,
            "archetype": self.archetype.value,
            "age": self.age,
            "dna": self.dna.to_dict(),
            "backstory": self.backstory,
            "personality_summary": self.personality_summary,
            "appearance_description": self.appearance_description,
            "portrait_path": self.portrait_path,
            "voice_sample_path": self.voice_sample_path,
            "voice_id": self.voice_id,
            "created_at": self.created_at,
            "generation_seed": self.generation_seed,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> CharacterCard:
        """Deserialize from dict."""
        dna = SexualPersonalityDNA.from_dict(d.get("dna", {}))
        return cls(
            id=d.get("id", uuid.uuid4().hex[:12]),
            name=d.get("name", ""),
            title=d.get("title", ""),
            gender=Gender(d.get("gender", "female")),
            archetype=Archetype(d.get("archetype", "queen")),
            age=d.get("age", 25),
            dna=dna,
            backstory=d.get("backstory", ""),
            personality_summary=d.get("personality_summary", ""),
            appearance_description=d.get("appearance_description", ""),
            portrait_path=d.get("portrait_path"),
            voice_sample_path=d.get("voice_sample_path"),
            voice_id=d.get("voice_id", ""),
            created_at=d.get("created_at", datetime.utcnow().isoformat()),
            generation_seed=d.get("generation_seed"),
            tags=d.get("tags", []),
        )

    @property
    def display_name(self) -> str:
        """Name with title for display."""
        if self.title:
            return f"{self.name}, {self.title}"
        return self.name

    @property
    def renpy_tag(self) -> str:
        """Ren'Py-safe character tag (lowercase, underscores)."""
        return self.name.lower().replace(" ", "_").replace("'", "")
