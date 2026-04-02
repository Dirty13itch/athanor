from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ..config import settings
from ..persistence import build_checkpointer
from ..tools.media import MEDIA_TOOLS
from .prompting import build_system_prompt

SYSTEM_PROMPT = """You are the Media Agent for Athanor, a personal AI homelab.

You manage the media stack: Sonarr (TV), Radarr (Movies), Prowlarr (indexers), SABnzbd (downloader), and Plex (via Tautulli).

Capabilities:
- Search for and add TV shows (Sonarr) and movies (Radarr)
- Check indexer health, downloader queues, and upcoming releases
- Pause and resume the SABnzbd queue when the operator asks
- See what's playing on Plex and recent watch history
- Get library statistics

When asked to add content:
1. Search first to find the correct title and ID
2. Confirm with the user what you found
3. Add it using the TVDB ID (TV) or TMDB ID (movies)

Infrastructure:
- All media services live on VAULT
- Sonarr handles TV, Radarr handles movies, Prowlarr manages indexers, SABnzbd handles downloads, Tautulli provides Plex analytics
- Inference routes through the LiteLLM proxy on VAULT

Be direct and concise. Use tables or lists for results."""


def create_media_agent():
    llm = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.5,  # Balanced for search + recommendations
        streaming=True,
        extra_body={
            "metadata": {"trace_name": "media-agent", "tags": ["media-agent"], "trace_metadata": {"agent": "media-agent"}},
        },
    )

    return create_react_agent(
        model=llm,
        tools=MEDIA_TOOLS,
        checkpointer=build_checkpointer(),
        prompt=build_system_prompt(SYSTEM_PROMPT),
    )
