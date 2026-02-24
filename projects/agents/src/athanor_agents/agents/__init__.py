from .general import create_general_assistant
from .media import create_media_agent
from .research import create_research_agent
from .creative import create_creative_agent

_AGENTS: dict = {}


def _init_agents():
    if not _AGENTS:
        _AGENTS["general-assistant"] = create_general_assistant()
        _AGENTS["media-agent"] = create_media_agent()
        _AGENTS["research-agent"] = create_research_agent()
        _AGENTS["creative-agent"] = create_creative_agent()


def get_agent(name: str):
    _init_agents()
    return _AGENTS.get(name)


def list_agents() -> list[str]:
    _init_agents()
    return list(_AGENTS.keys())


# Agent display metadata (name, description, icon)
_AGENT_META = {
    "general-assistant": {
        "name": "General Assistant",
        "description": "System monitoring, GPU metrics, storage info, and infrastructure queries",
        "icon": "terminal",
    },
    "media-agent": {
        "name": "Media Agent",
        "description": "Search and add TV shows & movies, check downloads, Plex activity",
        "icon": "film",
    },
    "home-agent": {
        "name": "Home Agent",
        "description": "Smart home control — lights, climate, automations via Home Assistant",
        "icon": "home",
    },
    "research-agent": {
        "name": "Research Agent",
        "description": "Web research, knowledge search, infrastructure queries — structured reports with citations",
        "icon": "search",
    },
    "creative-agent": {
        "name": "Creative Agent",
        "description": "Image generation via ComfyUI Flux — text-to-image, queue management, generation history",
        "icon": "image",
    },
}


def get_agent_info() -> list[dict]:
    """Return metadata for all agents with dynamically discovered tool names."""
    _init_agents()
    result = []
    for agent_id, agent in _AGENTS.items():
        meta = _AGENT_META.get(agent_id, {"name": agent_id, "description": "", "icon": "terminal"})
        # Extract tool names from the LangGraph agent
        tools = []
        try:
            # create_react_agent wraps ToolNode in a PregelNode
            # Path: agent.nodes["tools"].bound.tools_by_name
            tool_node = agent.nodes.get("tools")
            if tool_node and hasattr(tool_node, "bound"):
                bound = tool_node.bound
                if hasattr(bound, "tools_by_name"):
                    tools = list(bound.tools_by_name.keys())
        except Exception:
            pass
        result.append({
            "id": agent_id,
            "name": meta["name"],
            "description": meta["description"],
            "icon": meta["icon"],
            "tools": tools,
            "status": "ready",
        })
    return result
