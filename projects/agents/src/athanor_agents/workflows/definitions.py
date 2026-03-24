"""Built-in workflow definitions.

Each definition is a dict with:
    name: str
    description: str
    steps: list[dict] -- each step has agent_id, action, input_template, output_key

Template variables:
    {input}            -- the initial user input
    {<output_key>}     -- output from a previous step (by its output_key)
"""

WORKFLOW_DEFINITIONS: list[dict] = [
    {
        "name": "deep_research",
        "description": (
            "Multi-step research pipeline: search for information, "
            "synthesize findings into a report, then store the result "
            "in the knowledge base."
        ),
        "steps": [
            {
                "agent_id": "research-agent",
                "action": "search",
                "input_template": (
                    "Search the web and knowledge base thoroughly for information on: {input}\n\n"
                    "Find at least 3 distinct sources. Return raw findings with source URLs."
                ),
                "output_key": "search_results",
            },
            {
                "agent_id": "research-agent",
                "action": "synthesize",
                "input_template": (
                    "Synthesize the following raw research findings into a structured report.\n\n"
                    "Original topic: {input}\n\n"
                    "Raw findings:\n{search_results}\n\n"
                    "Produce a well-organized summary with key findings, comparisons, "
                    "and actionable recommendations. Cite sources."
                ),
                "output_key": "report",
            },
            {
                "agent_id": "knowledge-agent",
                "action": "store",
                "input_template": (
                    "Store the following research report in the knowledge base.\n\n"
                    "Topic: {input}\n\n"
                    "Report:\n{report}\n\n"
                    "Upload this as a research document with appropriate metadata."
                ),
                "output_key": "store_result",
            },
        ],
    },
    {
        "name": "media_pipeline",
        "description": (
            "Creative media workflow: generate a detailed image description, "
            "send it to ComfyUI for generation, then review the result."
        ),
        "steps": [
            {
                "agent_id": "creative-agent",
                "action": "describe",
                "input_template": (
                    "Create a detailed, vivid image generation prompt based on this request: {input}\n\n"
                    "The prompt should be optimized for Flux text-to-image generation. "
                    "Include specific details about composition, lighting, style, and mood. "
                    "Return ONLY the prompt text, no commentary."
                ),
                "output_key": "image_prompt",
            },
            {
                "agent_id": "creative-agent",
                "action": "generate",
                "input_template": (
                    "Generate an image using this prompt:\n{image_prompt}\n\n"
                    "Use the generate_image tool with default settings (1024x1024, 20 steps)."
                ),
                "output_key": "generation_result",
            },
            {
                "agent_id": "general-assistant",
                "action": "review",
                "input_template": (
                    "Review this image generation result and summarize for the user.\n\n"
                    "Original request: {input}\n"
                    "Prompt used: {image_prompt}\n"
                    "Generation result: {generation_result}\n\n"
                    "Provide a concise status update."
                ),
                "output_key": "review",
            },
        ],
    },
    {
        "name": "daily_digest",
        "description": (
            "Daily briefing workflow: collect signals from feeds and services, "
            "then summarize into a digestible briefing."
        ),
        "steps": [
            {
                "agent_id": "general-assistant",
                "action": "collect-signals",
                "input_template": (
                    "Collect a status snapshot for the daily digest. Check:\n"
                    "1. Current service health across all nodes\n"
                    "2. GPU utilization and model status\n"
                    "3. Any recent task completions or failures\n\n"
                    "Additional focus areas: {input}\n\n"
                    "Return raw data points, not a summary."
                ),
                "output_key": "raw_signals",
            },
            {
                "agent_id": "research-agent",
                "action": "summarize",
                "input_template": (
                    "Create a concise daily digest from these raw signals:\n\n"
                    "{raw_signals}\n\n"
                    "Format as a brief executive summary with:\n"
                    "- System health (1-2 sentences)\n"
                    "- Key events since last digest\n"
                    "- Action items or anomalies requiring attention\n"
                    "- Resource utilization highlights\n\n"
                    "Keep it under 500 words. Be direct."
                ),
                "output_key": "digest",
            },
        ],
    },
]
