from langchain_core.tools import tool

from ..subscriptions import LeaseRequest, preview_execution_lease


@tool
def request_execution_lease(
    requester: str,
    task_class: str,
    sensitivity: str = "repo_internal",
    interactive: bool = False,
    expected_context: str = "medium",
    parallelism: str = "low",
) -> str:
    """Request a brokered execution lease before recommending off-cluster work.

    Use this when a task may benefit from Anthropic, OpenAI, Google, Moonshot,
    or Z.ai capacity instead of pure local execution. Set requester to the
    active agent id, such as coding-agent or research-agent. This tool returns
    the approved provider lane, why it was chosen, and the fallback chain.
    """

    lease = preview_execution_lease(
        LeaseRequest(
            requester=requester,
            task_class=task_class,
            sensitivity=sensitivity,
            interactive=interactive,
            expected_context=expected_context,
            parallelism=parallelism,
        )
    )
    fallback = ", ".join(lease.fallback) if lease.fallback else "none"
    return (
        f"Approved provider: {lease.provider}\n"
        f"Surface: {lease.surface}\n"
        f"Privacy: {lease.privacy}\n"
        f"Parallel children: {lease.max_parallel_children}\n"
        f"Fallback: {fallback}\n"
        f"Reason: {lease.reason}"
    )


SUBSCRIPTION_TOOLS = [request_execution_lease]
