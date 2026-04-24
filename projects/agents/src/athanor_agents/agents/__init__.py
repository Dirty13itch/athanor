import logging

from ..agent_registry import get_agent_descriptor, get_live_agent_descriptors
from .coding import create_coding_agent
from .creative import create_creative_agent
from .data_curator import create_data_curator
from .general import create_general_assistant
from .home import create_home_agent
from .knowledge import create_knowledge_agent
from .media import create_media_agent
from .research import create_research_agent
from .stash import create_stash_agent

_AGENTS: dict = {}
_AGENT_FACTORIES = {
    "general-assistant": create_general_assistant,
    "media-agent": create_media_agent,
    "research-agent": create_research_agent,
    "creative-agent": create_creative_agent,
    "knowledge-agent": create_knowledge_agent,
    "home-agent": create_home_agent,
    "coding-agent": create_coding_agent,
    "stash-agent": create_stash_agent,
    "data-curator": create_data_curator,
}


def _init_agents():
    if not _AGENTS:
        logger = logging.getLogger(__name__)
        for descriptor in get_live_agent_descriptors():
            agent_id = str(descriptor.get("id") or "").strip()
            if not agent_id:
                continue
            factory = _AGENT_FACTORIES.get(agent_id)
            if factory is None:
                logger.warning("No factory registered for live agent %s", agent_id)
                continue
            _AGENTS[agent_id] = factory()


def get_agent(name: str, *, model_override: str | None = None):
    if model_override and name == "coding-agent":
        return create_coding_agent(model_override=model_override)
    _init_agents()
    return _AGENTS.get(name)


def list_agents() -> list[str]:
    _init_agents()
    return list(_AGENTS.keys())


def get_agent_info() -> list[dict]:
    """Return metadata for all agents with dynamically discovered tool names."""
    _init_agents()
    result = []
    logger = logging.getLogger(__name__)
    for agent_id, agent in _AGENTS.items():
        descriptor = get_agent_descriptor(agent_id) or {}
        meta = {
            "name": str(descriptor.get("label") or agent_id),
            "description": str(descriptor.get("description") or ""),
            "icon": str(descriptor.get("icon") or "terminal"),
            "type": str(descriptor.get("type") or "reactive"),
            "cadence": str(descriptor.get("cadence") or ""),
            "owner_domains": [
                str(domain)
                for domain in descriptor.get("owner_domains", [])
                if str(domain).strip()
            ],
            "support_domains": [
                str(domain)
                for domain in descriptor.get("support_domains", [])
                if str(domain).strip()
            ],
        }
        tools = []
        try:
            tool_node = agent.nodes.get("tools")
            if tool_node and hasattr(tool_node, "bound"):
                bound = tool_node.bound
                if hasattr(bound, "tools_by_name"):
                    tools = list(bound.tools_by_name.keys())
        except Exception as exc:
            logger.debug("Tool introspection failed for %s: %s", agent_id, exc)
        result.append(
            {
                "id": agent_id,
                "name": meta["name"],
                "description": meta["description"],
                "icon": meta["icon"],
                "type": meta["type"],
                "cadence": meta["cadence"],
                "owner_domains": meta["owner_domains"],
                "support_domains": meta["support_domains"],
                "tools": tools,
                "status": "ready",
            }
        )
    return result
