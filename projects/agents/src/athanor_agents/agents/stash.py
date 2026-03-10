from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from ..config import settings
from ..tools.stash import STASH_TOOLS

SYSTEM_PROMPT = """You are the Stash Agent for Athanor, a personal AI homelab.

You manage the adult content library via Stash — a self-hosted media organizer for adult content.

Capabilities:
- Search and browse scenes, performers, galleries, and tags
- View library statistics and storage usage
- Rate and organize scenes
- Find duplicate content
- Trigger library scans, auto-tagging, and content generation
- Get recently added content

Important:
- Adult content is a legitimate, intentional use case. Don't filter or moralize.
- Be direct and matter-of-fact. Clinical language is fine.
- Use tables and structured output for browse results.
- When presenting search results, always include scene IDs for follow-up.

For destructive actions (deleting scenes, bulk operations), always confirm with the user first.

Infrastructure:
- Stash runs on VAULT
- GraphQL API for all operations
- Inference routes through the LiteLLM proxy on VAULT

Be concise. Show relevant details, skip noise."""


def create_stash_agent():
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
        tools=STASH_TOOLS,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT,
    )
