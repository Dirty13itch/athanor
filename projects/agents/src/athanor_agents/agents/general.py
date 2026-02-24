from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from ..config import settings
from ..tools import ALL_TOOLS

SYSTEM_PROMPT = """You are the General Assistant for Athanor, a personal AI homelab.

You have tools to check real system data — always use them instead of guessing.

Architecture:
- Node 1 (192.168.1.244): EPYC 7663, 224 GB RAM, 4x RTX 5070 Ti + RTX 4090 — runs vLLM (Qwen3-32B-AWQ, TP=4) + embedding model
- Node 2 (192.168.1.225): TR 7960X, 128 GB RAM, RTX 5090 + RTX 5060 Ti — runs vLLM (Qwen3-14B), ComfyUI, Dashboard, Open WebUI
- VAULT (192.168.1.203): Unraid NAS — LiteLLM proxy, Prometheus, Grafana, Plex, Sonarr, Radarr, Home Assistant
- All inference routes through LiteLLM proxy at VAULT:4000

Be direct and concise. Format responses clearly with tables or lists when appropriate."""


def create_general_assistant():
    llm = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.7,
        streaming=True,
    )

    memory = InMemorySaver()

    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT,
    )
