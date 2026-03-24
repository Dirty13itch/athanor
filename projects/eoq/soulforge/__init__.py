"""SoulForge Engine — procedural character generation for Empire of Broken Queens.

Pipeline: DNA -> Backstory (LLM) -> Portrait (ComfyUI) -> Voice (Speaches) -> CharacterCard
All traffic stays local. Zero cloud.
"""

from soulforge.dna import SexualPersonalityDNA, generate_random_dna, dna_to_description, crossover
from soulforge.character import CharacterCard, Gender, Archetype
from soulforge.engine import SoulForge
from soulforge.dialogue import generate_dialogue, build_character_system_prompt

__version__ = "0.1.0"
__all__ = [
    "SexualPersonalityDNA",
    "generate_random_dna",
    "dna_to_description",
    "crossover",
    "CharacterCard",
    "Gender",
    "Archetype",
    "SoulForge",
    "generate_dialogue",
    "build_character_system_prompt",
]
