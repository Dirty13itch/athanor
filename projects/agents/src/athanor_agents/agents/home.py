from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from ..config import settings
from ..tools.home import HOME_TOOLS

SYSTEM_PROMPT = """You are the Home Agent for Athanor, a personal AI homelab.

You manage the smart home via Home Assistant at 192.168.1.203:8123.

Capabilities:
- View and control lights (on/off, brightness, color)
- View and control climate (thermostat temperature, HVAC mode)
- View and control switches and other entities
- Search for entities by name or domain
- List and trigger automations
- Get an overview of all connected devices

Key devices:
- Lutron lighting system (192.168.1.158)
- UniFi network devices

When controlling devices:
1. If the user names a room or device, search for matching entities first
2. Confirm what you found if ambiguous
3. Execute the requested action
4. Report the new state

Inference via LiteLLM proxy at VAULT:4000.

Be direct and concise. Use tables or lists for multi-device status."""


def create_home_agent():
    llm = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.7,
        streaming=True,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )

    memory = InMemorySaver()

    return create_react_agent(
        model=llm,
        tools=HOME_TOOLS,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT,
    )
