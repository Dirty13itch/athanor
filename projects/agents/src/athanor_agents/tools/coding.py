"""Coding tools — code generation, review, and analysis.

These tools support the Coding Agent's ability to generate and review code.
The agent itself does the reasoning — these tools provide structured I/O.
"""

from langchain_core.tools import tool


@tool
def generate_code(
    specification: str,
    language: str = "python",
    context: str = "",
) -> str:
    """Generate code from a natural language specification.

    Use this when you need to produce code that implements a described behavior.
    Write clean, well-structured code that follows the conventions described in the spec.

    Args:
        specification: What the code should do — be specific about inputs, outputs, and behavior
        language: Programming language (python, typescript, bash, yaml, etc.)
        context: Additional context — existing code patterns, imports, project conventions
    """
    # This tool is a structured prompt wrapper — the LLM does the actual generation.
    # The tool enforces structured input/output format.
    parts = [f"Generate {language} code for the following specification:"]
    parts.append(f"\n## Specification\n{specification}")
    if context:
        parts.append(f"\n## Context\n{context}")
    parts.append("\n## Requirements")
    parts.append("- Write only the code, no explanations unless critical")
    parts.append("- Include necessary imports")
    parts.append("- Follow existing patterns from the context if provided")
    parts.append("- Use type hints (Python) or TypeScript types where appropriate")
    return "\n".join(parts)


@tool
def review_code(code: str, focus: str = "") -> str:
    """Review code for bugs, security issues, and quality problems.

    Analyzes provided code and returns specific, actionable feedback.

    Args:
        code: The code to review
        focus: Optional focus area (e.g., "security", "performance", "correctness", "style")
    """
    parts = ["Review the following code:"]
    parts.append(f"\n```\n{code}\n```")
    if focus:
        parts.append(f"\nFocus on: {focus}")
    parts.append("\nProvide:")
    parts.append("1. Bugs or logical errors (with line references)")
    parts.append("2. Security concerns (injection, XSS, OWASP)")
    parts.append("3. Specific improvement suggestions")
    parts.append("4. Overall assessment (ship / needs changes / needs redesign)")
    return "\n".join(parts)


@tool
def explain_code(code: str, question: str = "") -> str:
    """Explain what code does and how it works.

    Provides a clear explanation of code logic, useful for understanding
    unfamiliar codebases or complex algorithms.

    Args:
        code: The code to explain
        question: Specific question about the code (optional)
    """
    parts = ["Explain the following code:"]
    parts.append(f"\n```\n{code}\n```")
    if question:
        parts.append(f"\nSpecific question: {question}")
    parts.append("\nProvide:")
    parts.append("1. High-level purpose (one sentence)")
    parts.append("2. Step-by-step walkthrough of the logic")
    parts.append("3. Key design decisions and trade-offs")
    return "\n".join(parts)


@tool
def transform_code(code: str, instruction: str) -> str:
    """Transform or refactor code according to an instruction.

    Apply a specific transformation to existing code — refactoring,
    pattern changes, API migration, etc.

    Args:
        code: The original code to transform
        instruction: What transformation to apply (e.g., "convert to async", "add error handling")
    """
    parts = ["Transform the following code:"]
    parts.append(f"\n```\n{code}\n```")
    parts.append(f"\nTransformation: {instruction}")
    parts.append("\nRequirements:")
    parts.append("- Preserve the original behavior unless the instruction changes it")
    parts.append("- Keep the same style and conventions")
    parts.append("- Output only the transformed code")
    return "\n".join(parts)


CODING_TOOLS = [generate_code, review_code, explain_code, transform_code]
