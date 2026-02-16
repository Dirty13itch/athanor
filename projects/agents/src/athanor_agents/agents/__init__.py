from .general import create_general_assistant

_AGENTS: dict = {}


def _init_agents():
    if not _AGENTS:
        _AGENTS["general-assistant"] = create_general_assistant()


def get_agent(name: str):
    _init_agents()
    return _AGENTS.get(name)


def list_agents() -> list[str]:
    _init_agents()
    return list(_AGENTS.keys())
