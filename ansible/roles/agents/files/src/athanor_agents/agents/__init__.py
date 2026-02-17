from .general import create_general_assistant
from .media import create_media_agent
from ..config import settings

_AGENTS: dict = {}


def _init_agents():
    if not _AGENTS:
        _AGENTS["general-assistant"] = create_general_assistant()
        _AGENTS["media-agent"] = create_media_agent()

        if settings.ha_token:
            from .home import create_home_agent

            _AGENTS["home-agent"] = create_home_agent()


def get_agent(name: str):
    _init_agents()
    return _AGENTS.get(name)


def list_agents() -> list[str]:
    _init_agents()
    return list(_AGENTS.keys())
