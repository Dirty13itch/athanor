"""19-Trait Sexual Personality DNA System.

Each trait is a float 0.0-1.0. The DNA encodes a character's full
sexual personality, used to drive dialogue style, scene preferences,
and relationship dynamics in Empire of Broken Queens.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, fields, asdict
from typing import Dict, List, Tuple


TRAIT_NAMES: List[str] = [
    "dominance", "submission", "exhibitionism", "voyeurism",
    "sadism", "masochism", "romanticism", "aggression",
    "tenderness", "playfulness", "jealousy", "possessiveness",
    "loyalty", "deception", "curiosity", "inhibition",
    "stamina", "sensitivity", "charisma",
]

# Trait pairs that should be inversely correlated for internal consistency.
INVERSE_PAIRS: List[Tuple[str, str]] = [
    ("dominance", "submission"),
    ("sadism", "masochism"),
    ("loyalty", "deception"),
    ("aggression", "tenderness"),
    ("inhibition", "exhibitionism"),
]

# Trait pairs that should be positively correlated.
CORRELATED_PAIRS: List[Tuple[str, str]] = [
    ("dominance", "aggression"),
    ("submission", "sensitivity"),
    ("romanticism", "tenderness"),
    ("possessiveness", "jealousy"),
    ("playfulness", "curiosity"),
    ("charisma", "exhibitionism"),
]

# Descriptors for low/mid/high values of each trait.
TRAIT_DESCRIPTORS: Dict[str, Tuple[str, str, str]] = {
    "dominance":      ("submissive by nature", "switches naturally", "commanding and dominant"),
    "submission":     ("resists being controlled", "selectively yielding", "deeply submissive"),
    "exhibitionism":  ("intensely private", "selectively revealing", "thrives on being watched"),
    "voyeurism":      ("averts their gaze", "casually observant", "obsessive voyeur"),
    "sadism":         ("gentle to a fault", "enjoys light edge play", "drawn to inflicting pain"),
    "masochism":      ("avoids all pain", "enjoys a sting", "craves suffering"),
    "romanticism":    ("coldly pragmatic", "appreciates gestures", "hopelessly romantic"),
    "aggression":     ("passive and yielding", "assertive when needed", "raw aggression"),
    "tenderness":     ("emotionally distant", "warm in private", "overwhelmingly tender"),
    "playfulness":    ("deadly serious", "dry humor", "endlessly playful and teasing"),
    "jealousy":       ("secure and unbothered", "mildly territorial", "consumed by jealousy"),
    "possessiveness": ("open and sharing", "selective about boundaries", "fiercely possessive"),
    "loyalty":        ("self-serving above all", "conditionally loyal", "loyal unto death"),
    "deception":      ("transparent to a fault", "strategic with truth", "masterful deceiver"),
    "curiosity":      ("set in their ways", "open to new things", "insatiably curious"),
    "inhibition":     ("wild and uninhibited", "has some boundaries", "deeply repressed"),
    "stamina":        ("tires quickly", "average endurance", "seemingly inexhaustible"),
    "sensitivity":    ("thick-skinned", "normally responsive", "exquisitely sensitive"),
    "charisma":       ("wallflower energy", "pleasant company", "magnetically charismatic"),
}


@dataclass
class SexualPersonalityDNA:
    """19-trait sexual personality encoding. All traits are floats in [0.0, 1.0]."""

    dominance: float = 0.5
    submission: float = 0.5
    exhibitionism: float = 0.5
    voyeurism: float = 0.5
    sadism: float = 0.5
    masochism: float = 0.5
    romanticism: float = 0.5
    aggression: float = 0.5
    tenderness: float = 0.5
    playfulness: float = 0.5
    jealousy: float = 0.5
    possessiveness: float = 0.5
    loyalty: float = 0.5
    deception: float = 0.5
    curiosity: float = 0.5
    inhibition: float = 0.5
    stamina: float = 0.5
    sensitivity: float = 0.5
    charisma: float = 0.5

    def __post_init__(self) -> None:
        for f in fields(self):
            val = getattr(self, f.name)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{f.name} must be in [0.0, 1.0], got {val}")

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> SexualPersonalityDNA:
        return cls(**{k: v for k, v in d.items() if k in TRAIT_NAMES})

    def dominant_traits(self, threshold: float = 0.7) -> List[str]:
        """Return traits above the given threshold, sorted by value descending."""
        return sorted(
            [f.name for f in fields(self) if getattr(self, f.name) >= threshold],
            key=lambda t: getattr(self, t),
            reverse=True,
        )

    def recessive_traits(self, threshold: float = 0.3) -> List[str]:
        """Return traits below the given threshold, sorted by value ascending."""
        return sorted(
            [f.name for f in fields(self) if getattr(self, f.name) <= threshold],
            key=lambda t: getattr(self, t),
        )


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def generate_random_dna(
    *,
    bias: Dict[str, float] | None = None,
    consistency_strength: float = 0.6,
) -> SexualPersonalityDNA:
    """Generate a random but internally consistent DNA.

    Args:
        bias: Optional dict of trait_name -> target_value to bias generation.
        consistency_strength: How strongly inverse/correlated pairs are enforced (0-1).
    """
    # Start with random base values.
    traits: Dict[str, float] = {t: random.random() for t in TRAIT_NAMES}

    # Apply explicit biases.
    if bias:
        for trait, target in bias.items():
            if trait in traits:
                traits[trait] = _clamp(target + random.gauss(0, 0.05))

    # Enforce inverse correlations.
    for a, b in INVERSE_PAIRS:
        avg = (traits[a] + (1.0 - traits[b])) / 2.0
        traits[a] = _clamp(traits[a] * (1 - consistency_strength) + avg * consistency_strength)
        traits[b] = _clamp(
            traits[b] * (1 - consistency_strength) + (1.0 - avg) * consistency_strength
        )

    # Enforce positive correlations.
    for a, b in CORRELATED_PAIRS:
        avg = (traits[a] + traits[b]) / 2.0
        traits[a] = _clamp(traits[a] * (1 - consistency_strength * 0.5) + avg * consistency_strength * 0.5)
        traits[b] = _clamp(traits[b] * (1 - consistency_strength * 0.5) + avg * consistency_strength * 0.5)

    # Add micro-noise so no two characters are identical.
    traits = {k: _clamp(v + random.gauss(0, 0.02)) for k, v in traits.items()}

    return SexualPersonalityDNA(**traits)


def dna_to_description(dna: SexualPersonalityDNA) -> str:
    """Convert DNA floats to a natural language personality description."""
    lines: List[str] = []

    for trait_name in TRAIT_NAMES:
        val = getattr(dna, trait_name)
        low, mid, high = TRAIT_DESCRIPTORS[trait_name]
        if val < 0.33:
            desc = low
        elif val < 0.67:
            desc = mid
        else:
            desc = high
        lines.append(f"- {trait_name.replace('_', ' ').title()}: {desc} ({val:.2f})")

    # Highlight extremes.
    dominant = dna.dominant_traits(0.8)
    recessive = dna.recessive_traits(0.2)

    summary_parts: List[str] = []
    if dominant:
        summary_parts.append(f"Defining traits: {', '.join(dominant)}")
    if recessive:
        summary_parts.append(f"Suppressed traits: {', '.join(recessive)}")

    header = " | ".join(summary_parts) if summary_parts else "Balanced personality"

    return f"{header}\n\n" + "\n".join(lines)


def crossover(
    parent_a: SexualPersonalityDNA,
    parent_b: SexualPersonalityDNA,
    *,
    mutation_rate: float = 0.1,
    mutation_strength: float = 0.15,
) -> SexualPersonalityDNA:
    """Genetic crossover: blend two parents with optional mutation.

    Uses uniform crossover with per-trait coin flip, then applies
    random mutations. Result is clamped and consistency-checked.
    """
    child_traits: Dict[str, float] = {}

    for trait_name in TRAIT_NAMES:
        a_val = getattr(parent_a, trait_name)
        b_val = getattr(parent_b, trait_name)

        # Uniform crossover with blend.
        if random.random() < 0.5:
            base = a_val
        else:
            base = b_val

        # Blend toward the other parent slightly.
        blend = random.uniform(0.2, 0.8)
        blended = base * blend + (a_val + b_val) / 2 * (1 - blend)

        # Mutation.
        if random.random() < mutation_rate:
            blended += random.gauss(0, mutation_strength)

        child_traits[trait_name] = _clamp(blended)

    return SexualPersonalityDNA(**child_traits)
