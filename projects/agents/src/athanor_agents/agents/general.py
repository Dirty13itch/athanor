from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from ..config import settings
from ..tools import ALL_TOOLS

SYSTEM_PROMPT = """You are the General Assistant for Athanor, a personal AI homelab.

You have tools to check real system data — always use them instead of guessing.

Architecture:
- Node 1 (192.168.1.244): EPYC 7663, 224 GB RAM, 4x RTX 5070 Ti — runs vLLM (Qwen3-32B-AWQ, TP=4)
- Node 2 (192.168.1.225): Ryzen 9 9950X, 128 GB RAM, RTX 5090 + RTX 4090 — runs ComfyUI, Dashboard, Open WebUI
- VAULT (192.168.1.203): Unraid NAS — Prometheus, Grafana, Plex, Sonarr, Radarr, Home Assistant

Be direct and concise. Format responses clearly with tables or lists when appropriate."""


def create_general_assistant():
    llm = ChatOpenAI(
        base_url=settings.vllm_base_url,
        api_key="not-needed",
        model=settings.vllm_model,
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
