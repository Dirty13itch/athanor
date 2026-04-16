from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .config import Settings, settings
from .services import join_url

ProjectKind = Literal["core", "tenant", "domain", "scaffold"]
ProjectLens = Literal["default", "system", "media", "creative", "eoq"]


@dataclass(frozen=True)
class ProjectNeed:
    type: str
    description: str
    agent: str
    priority: str
    output_format: str


@dataclass(frozen=True)
class ProjectDefinition:
    id: str
    name: str
    headline: str
    description: str
    status: str
    kind: ProjectKind
    first_class: bool
    lens: ProjectLens
    primary_route: str
    external_url: str | None
    operators: tuple[str, ...]
    agents: tuple[str, ...]
    location: str
    tech: str
    needs: tuple[ProjectNeed, ...]
    constraints: tuple[str, ...]

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "headline": self.headline,
            "description": self.description,
            "status": self.status,
            "kind": self.kind,
            "first_class": self.first_class,
            "lens": self.lens,
            "primary_route": self.primary_route,
            "external_url": self.external_url,
            "operators": list(self.operators),
            "agents": list(self.agents),
            "needs_count": len(self.needs),
            "constraints": list(self.constraints),
            "location": self.location,
            "tech": self.tech,
        }

    def to_detail_dict(self) -> dict[str, object]:
        detail = self.to_summary_dict()
        detail["needs"] = [asdict(need) for need in self.needs]
        return detail

    def to_workplanner_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "location": self.location,
            "tech": self.tech,
            "agents": list(self.agents),
            "needs": [asdict(need) for need in self.needs],
            "constraints": list(self.constraints),
        }


def build_project_registry(config: Settings | None = None) -> dict[str, ProjectDefinition]:
    cfg = config or settings
    return {
        "athanor": ProjectDefinition(
            id="athanor",
            name="Athanor",
            headline="Core operating environment for system state, workforce orchestration, and operator judgment.",
            description=(
                "The system itself: dashboard, agents, monitoring, memory, deployment, and the one-person-maintainable "
                "operating model."
            ),
            status="active",
            kind="core",
            first_class=True,
            lens="system",
            primary_route="/",
            external_url=None,
            operators=("Shaun", "Claude"),
            agents=("general-assistant", "coding-agent", "knowledge-agent", "research-agent"),
            location="projects/{agents,dashboard}/, ansible/, docs/, scripts/",
            tech="FastAPI agents, Next.js dashboard, Redis/Qdrant/Neo4j memory, Ansible deployment",
            needs=(
                ProjectNeed(
                    type="product",
                    description="Push Command Center, workforce, and project-platform convergence without topology drift.",
                    agent="coding-agent",
                    priority="high",
                    output_format="Code, UI, API, and contract tests",
                ),
                ProjectNeed(
                    type="research",
                    description="Audit routing, dependency, and deployment drift against the Athanor Next roadmap.",
                    agent="research-agent",
                    priority="high",
                    output_format="Structured audit with concrete remediation",
                ),
                ProjectNeed(
                    type="knowledge",
                    description="Keep runbooks, specs, and architectural docs aligned with the live operator model.",
                    agent="knowledge-agent",
                    priority="normal",
                    output_format="Docs deltas, updates, and traceable notes",
                ),
            ),
            constraints=(
                "Favor one-person maintainability over architectural novelty.",
                "Infrastructure work is an enabler, not the product.",
                "Preserve centralized runtime contracts and keep drift tests current.",
            ),
        ),
        "eoq": ProjectDefinition(
            id="eoq",
            name="Empire of Broken Queens",
            headline="First first-class tenant for creative generation, dialogue, and cinematic interaction.",
            description=(
                "AI-driven interactive dark-fantasy game where scene flow, dialogue, memory, and visual generation are "
                "part of the same tenant platform."
            ),
            status="active",
            kind="tenant",
            first_class=True,
            lens="eoq",
            primary_route="/workplanner?project=eoq",
            external_url=cfg.eoq_url,
            operators=("Claude", "creative-agent", "coding-agent"),
            agents=("creative-agent", "coding-agent", "research-agent", "knowledge-agent"),
            location="projects/eoq/ (Workshop app lane)",
            tech="Next.js, streamed dialogue APIs, ComfyUI generation, Qdrant/Neo4j-backed context",
            needs=(
                ProjectNeed(
                    type="content",
                    description="Create branching scenes, character state, and authored hooks that raise narrative momentum.",
                    agent="coding-agent",
                    priority="high",
                    output_format="TypeScript/JSON scene logic and dialogue assets",
                ),
                ProjectNeed(
                    type="assets",
                    description="Generate portrait, character, and scene packs that match the approved dark-fantasy lane.",
                    agent="creative-agent",
                    priority="high",
                    output_format="ComfyUI image outputs and prompt packs",
                ),
                ProjectNeed(
                    type="research",
                    description="Expand references, adjacent mechanics, and story interaction patterns that fit the tenant identity.",
                    agent="research-agent",
                    priority="normal",
                    output_format="Research brief with concrete design implications",
                ),
            ),
            constraints=(
                "Adult content is intentional and should not be censored out of the creative pipeline.",
                "All project prompts, outputs, and interface copy stay in English.",
                "Keep the tenant integrated into Athanor, not treated as a disconnected side app.",
            ),
        ),
        "kindred": ProjectDefinition(
            id="kindred",
            name="Kindred",
            headline="Scaffolded future tenant in concept and research mode.",
            description=(
                "Passion-based social matching project focused on intent, drive, and shared care rather than shallow profile matching."
            ),
            status="scaffolded",
            kind="scaffold",
            first_class=False,
            lens="default",
            primary_route="/workplanner?project=kindred",
            external_url=None,
            operators=("Claude", "research-agent"),
            agents=("research-agent",),
            location="docs/projects/kindred/ and future tenant scaffold",
            tech="Concept and requirements stage",
            needs=(
                ProjectNeed(
                    type="research",
                    description="Deepen the concept, product model, and privacy-aware matching architecture before any scaffold push.",
                    agent="research-agent",
                    priority="low",
                    output_format="Research memo and product framing",
                ),
            ),
            constraints=(
                "Keep work at concept depth until Shaun explicitly promotes it to an active build lane.",
                "Avoid building UI or backend scaffolds before the product model is firmer.",
            ),
        ),
        "ulrich-energy": ProjectDefinition(
            id="ulrich-energy",
            name="Ulrich Energy",
            headline="Scaffolded operational tenant for field workflows, reporting, and client-facing energy work.",
            description=(
                "Mobile-first workflow platform for inspections, reports, project status, and energy-audit operations."
            ),
            status="scaffolded",
            kind="scaffold",
            first_class=False,
            lens="default",
            primary_route="/workplanner?project=ulrich-energy",
            external_url=None,
            operators=("Claude", "coding-agent", "research-agent"),
            agents=("coding-agent", "research-agent", "knowledge-agent"),
            location="projects/ulrich-energy/ and docs/projects/ulrich-energy/",
            tech="Next.js scaffold, API stubs, requirements, mobile-first PWA direction",
            needs=(
                ProjectNeed(
                    type="product",
                    description="Turn the current scaffold into a coherent operator and field workflow with concrete data contracts.",
                    agent="coding-agent",
                    priority="normal",
                    output_format="Typed app scaffolding, API routes, and task-ready implementation slices",
                ),
                ProjectNeed(
                    type="research",
                    description="Refine workflow sequencing, reporting expectations, and real user/operator constraints.",
                    agent="research-agent",
                    priority="low",
                    output_format="Requirements delta and workflow notes",
                ),
            ),
            constraints=(
                "Treat this as a scaffolded tenant until Shaun promotes it into the active build lane.",
                "Prefer platform-aligned primitives over bespoke one-off architecture.",
            ),
        ),
        "media": ProjectDefinition(
            id="media",
            name="Media Library",
            headline="Operational domain project spanning curation, acquisition, and catalog quality.",
            description=(
                "Plex, Sonarr, Radarr, Tautulli, SABnzbd, and Stash working together as a curated media domain."
            ),
            status="operational",
            kind="domain",
            first_class=False,
            lens="media",
            primary_route="/media",
            external_url=join_url(cfg.plex_url, "/web"),
            operators=("media-agent",),
            agents=("media-agent", "stash-agent"),
            location="VAULT media stack",
            tech="Plex, Sonarr, Radarr, Tautulli, SABnzbd, Stash",
            needs=(
                ProjectNeed(
                    type="curation",
                    description="Recommend or queue high-signal additions based on Shaun's actual taste and viewing behavior.",
                    agent="media-agent",
                    priority="normal",
                    output_format="Curated suggestions or queued acquisitions with reasoning",
                ),
                ProjectNeed(
                    type="operations",
                    description="Surface queue failures, stuck downloads, and catalog issues before they go stale.",
                    agent="media-agent",
                    priority="low",
                    output_format="Operational status report with specific remediation",
                ),
            ),
            constraints=(
                "Prefer quality and fit over indiscriminate library growth.",
                "Treat disk pressure and queue health as real operational constraints.",
            ),
        ),
    }


def get_project_registry(config: Settings | None = None) -> dict[str, ProjectDefinition]:
    return build_project_registry(config)


def get_project_summaries(config: Settings | None = None) -> dict[str, dict[str, object]]:
    return {
        project_id: definition.to_summary_dict()
        for project_id, definition in get_project_registry(config).items()
    }


def get_project(project_id: str, config: Settings | None = None) -> dict[str, object] | None:
    definition = get_project_registry(config).get(project_id)
    return definition.to_detail_dict() if definition else None


def get_project_definitions(config: Settings | None = None) -> dict[str, dict[str, object]]:
    return {
        project_id: definition.to_workplanner_dict()
        for project_id, definition in get_project_registry(config).items()
    }
