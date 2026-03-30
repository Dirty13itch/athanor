"""Quality Cascade — chained task execution with evaluation loops.

A cascade is: Agent A generates → Agent B evaluates → if quality < threshold → Agent A refines → loop.

Cascades are the furnace's self-improving mechanism. They ensure output quality
improves over time without human intervention.

Usage:
    from .cascade import run_creative_cascade, run_code_quality_cascade
    await run_creative_cascade()  # Called from scheduler
"""

import asyncio
import json
import logging
import time

logger = logging.getLogger(__name__)

CASCADE_KEY = "athanor:cascade:state"
MAX_REFINEMENT_LOOPS = 3
QUALITY_THRESHOLD = 0.6
CASCADE_TIMEOUT = 600  # 10 min max per cascade


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def _submit_and_wait(
    agent: str,
    prompt: str,
    timeout: int = 300,
    *,
    autonomy_managed: bool = False,
) -> dict:
    """Submit a task and wait for completion. Returns the task dict."""
    from .tasks import get_task, submit_governed_task

    submission = await submit_governed_task(
        agent=agent,
        prompt=prompt,
        priority="normal",
        metadata={
            "source": "cascade",
            "cascade_timeout": timeout,
            "_autonomy_managed": autonomy_managed,
        },
        source="cascade",
    )
    task = submission.task

    start = time.time()
    while time.time() - start < timeout:
        current = await get_task(task.id)
        if current and current.status in ("completed", "failed", "cancelled"):
            return current.to_dict()
        await asyncio.sleep(5)

    return {"id": task.id, "status": "timeout", "error": f"Cascade task timed out after {timeout}s"}


async def run_creative_cascade(*, autonomy_managed: bool = False) -> dict:
    """Run a creative quality cascade: generate → evaluate → refine → loop.

    1. Creative agent generates an image for the queen with fewest assets
    2. Research agent evaluates the output quality
    3. If quality < threshold, creative agent refines with feedback
    4. Loop up to MAX_REFINEMENT_LOOPS times

    Returns cascade result dict with all task IDs and final quality.
    """
    cascade_id = f"creative-{int(time.time())}"
    results = {
        "cascade_id": cascade_id,
        "type": "creative",
        "started_at": time.time(),
        "loops": [],
    }

    try:
        for loop_num in range(MAX_REFINEMENT_LOOPS):
            loop_result = {"loop": loop_num + 1}

            # Step 1: Generate
            if loop_num == 0:
                gen_prompt = (
                    "Generate a portrait for the EoBQ queen with the fewest gallery assets. "
                    "Use generate_with_likeness with her exact physical blueprint. "
                    "Photorealistic, studio lighting, 8K. Report which queen and the prompt used."
                )
            else:
                # Refinement — use feedback from evaluation
                prev_feedback = results["loops"][-1].get("eval_feedback", "improve quality")
                gen_prompt = (
                    f"REFINEMENT ROUND {loop_num + 1}: Re-generate the previous portrait with improvements. "
                    f"Feedback from evaluation: {prev_feedback}\n"
                    f"Use a different seed. Adjust the prompt based on the feedback. "
                    f"Focus on fixing the specific issues mentioned."
                )

            gen_task = await _submit_and_wait(
                "creative-agent",
                gen_prompt,
                timeout=180,
                autonomy_managed=autonomy_managed,
            )
            loop_result["generate"] = {
                "task_id": gen_task.get("id"),
                "status": gen_task.get("status"),
            }

            if gen_task.get("status") != "completed":
                loop_result["outcome"] = "generation_failed"
                results["loops"].append(loop_result)
                break

            # Step 2: Evaluate (use general-assistant as evaluator since it can access gallery)
            eval_prompt = (
                "Evaluate the most recently generated image in the gallery. "
                "Check generation history and look at the latest output. "
                "Score these dimensions (0.0-1.0):\n"
                "1. prompt_adherence: Does the image match what was requested?\n"
                "2. realism: Does it look photorealistic, not AI-generated?\n"
                "3. anatomy: Are body proportions correct? No extra fingers, distorted limbs?\n"
                "4. composition: Good framing, lighting, and visual appeal?\n"
                "Give an overall quality score (0.0-1.0) and specific feedback for improvement. "
                "Be critical — generic 'looks good' is not helpful."
            )

            eval_task = await _submit_and_wait(
                "general-assistant",
                eval_prompt,
                timeout=120,
                autonomy_managed=autonomy_managed,
            )
            loop_result["evaluate"] = {
                "task_id": eval_task.get("id"),
                "status": eval_task.get("status"),
            }

            # Parse quality from evaluation result
            eval_result = eval_task.get("result", "")
            quality_score = _extract_quality_score(eval_result)
            loop_result["quality_score"] = quality_score
            loop_result["eval_feedback"] = eval_result[:500] if eval_result else "no feedback"

            if quality_score >= QUALITY_THRESHOLD:
                loop_result["outcome"] = "accepted"
                results["loops"].append(loop_result)
                break
            else:
                loop_result["outcome"] = "needs_refinement"
                results["loops"].append(loop_result)
                # Continue to next loop for refinement

        results["final_quality"] = results["loops"][-1].get("quality_score", 0.0) if results["loops"] else 0.0
        results["total_loops"] = len(results["loops"])
        results["completed_at"] = time.time()
        results["duration_s"] = results["completed_at"] - results["started_at"]

    except Exception as e:
        results["error"] = str(e)
        logger.error("Creative cascade failed: %s", e)

    # Store cascade result in Redis
    try:
        r = await _get_redis()
        await r.hset(CASCADE_KEY, cascade_id, json.dumps(results))
    except Exception:
        pass

    return results


async def run_code_quality_cascade(*, autonomy_managed: bool = False) -> dict:
    """Run a code quality cascade: audit → fix → verify.

    1. Coding agent audits a component
    2. General assistant reviews the audit for accuracy
    3. If issues found, coding agent proposes fixes

    Returns cascade result dict.
    """
    cascade_id = f"code-{int(time.time())}"
    results = {
        "cascade_id": cascade_id,
        "type": "code_quality",
        "started_at": time.time(),
        "steps": [],
    }

    try:
        # Step 1: Audit
        audit_prompt = (
            "Pick one Python file from the agent server codebase that you haven't reviewed recently. "
            "Read it carefully. Look for:\n"
            "- Missing error handling (bare except, missing try/except around IO)\n"
            "- Type hints that could be added\n"
            "- Logic bugs or edge cases\n"
            "- Logging that could be more informative\n"
            "- Dead code or unused imports\n"
            "Write a detailed review. Be specific — cite line numbers and exact issues."
        )

        audit_task = await _submit_and_wait(
            "coding-agent",
            audit_prompt,
            timeout=180,
            autonomy_managed=autonomy_managed,
        )
        results["steps"].append({
            "step": "audit",
            "task_id": audit_task.get("id"),
            "status": audit_task.get("status"),
            "result_preview": (audit_task.get("result", "") or "")[:300],
        })

        # Step 2: Verify audit quality
        audit_result = audit_task.get("result", "")
        if audit_result and len(audit_result) > 100:
            verify_prompt = (
                f"A code audit was just completed. Review the findings for accuracy:\n\n"
                f"{audit_result[:1000]}\n\n"
                f"Are these real issues or false positives? Score the audit quality (0.0-1.0). "
                f"Flag any findings that seem incorrect."
            )

            verify_task = await _submit_and_wait(
                "general-assistant",
                verify_prompt,
                timeout=120,
                autonomy_managed=autonomy_managed,
            )
            results["steps"].append({
                "step": "verify",
                "task_id": verify_task.get("id"),
                "status": verify_task.get("status"),
            })

        results["completed_at"] = time.time()
        results["duration_s"] = results["completed_at"] - results["started_at"]

    except Exception as e:
        results["error"] = str(e)
        logger.error("Code quality cascade failed: %s", e)

    try:
        r = await _get_redis()
        await r.hset(CASCADE_KEY, cascade_id, json.dumps(results))
    except Exception:
        pass

    return results


def _extract_quality_score(text: str) -> float:
    """Extract a quality score from evaluation text. Returns 0.0-1.0."""
    if not text:
        return 0.0

    import re

    # Look for explicit score patterns
    patterns = [
        r"overall[:\s]*(?:quality[:\s]*)?(?:score[:\s]*)?(\d+\.?\d*)",
        r"quality[:\s]*(?:score[:\s]*)?(\d+\.?\d*)",
        r"score[:\s]*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*/\s*1\.0",
        r"(\d+\.?\d*)\s*/\s*10",
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            score = float(match.group(1))
            if score > 1.0 and score <= 10.0:
                score /= 10.0  # Normalize X/10 to 0-1
            if score > 10.0:
                score /= 100.0  # Normalize percentage
            return min(1.0, max(0.0, score))

    # Heuristic: if text contains positive words, assume decent quality
    positive = sum(1 for w in ["good", "excellent", "strong", "high", "realistic", "accurate"]
                   if w in text.lower())
    negative = sum(1 for w in ["poor", "bad", "distorted", "unrealistic", "artifact", "wrong"]
                   if w in text.lower())

    if positive > negative:
        return 0.7
    elif negative > positive:
        return 0.3
    return 0.5  # Neutral default
