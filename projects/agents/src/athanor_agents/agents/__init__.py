from .general import create_general_assistant
from .media import create_media_agent

_AGENTS: dict = {}


def _init_agents():
    if not _AGENTS:
        _AGENTS["general-assistant"] = create_general_assistant()
        _AGENTS["media-agent"] = create_media_agent()


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
            # create_react_agent stores tools in the graph's nodes
            # Access via the agent's tool node
            tool_node = agent.nodes.get("tools")
            if tool_node and hasattr(tool_node, "tools_by_name"):
                tools = list(tool_node.tools_by_name.keys())
            elif hasattr(agent, "tools"):
                tools = [t.name for t in agent.tools]
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
