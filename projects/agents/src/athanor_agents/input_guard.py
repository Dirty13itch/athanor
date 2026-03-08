"""Input guard — detect prompt injection, data exfiltration, and command injection.

Fast regex-based scanning (<5ms). Philosophy: DETECT and LOG, don't aggressively
block. False positives are worse than false negatives for a sovereign system.

Risk scoring: each pattern contributes to a 0.0-1.0 score.
  - Above 0.7: block and log (clear attack)
  - Below 0.7: pass with warning logged

All detections logged to stderr for Loki/Grafana pickup.
"""

import logging
import re
import sys
import unicodedata

logger = logging.getLogger("athanor.input_guard")
# Ensure warnings go to stderr even if root logger isn't configured
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [INPUT_GUARD] %(levelname)s %(message)s"
    ))
    logger.addHandler(_handler)
    logger.setLevel(logging.DEBUG)


# --- Invisible Unicode detection ---

# Zero-width and formatting characters that have no business in chat input
_INVISIBLE_CHARS = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f"   # zero-width, LTR/RTL marks
    r"\u2060\u2061\u2062\u2063\u2064"     # word joiner, invisible operators
    r"\ufeff"                              # BOM / zero-width no-break space
    r"\u00ad"                              # soft hyphen
    r"\u034f"                              # combining grapheme joiner
    r"\u061c"                              # Arabic letter mark
    r"\u115f\u1160"                        # Hangul fillers
    r"\u17b4\u17b5"                        # Khmer vowel inherent
    r"\u180e"                              # Mongolian vowel separator
    r"\uffa0]"                             # halfwidth Hangul filler
)

# RTL override characters used to visually disguise text
_RTL_OVERRIDES = re.compile(r"[\u202a-\u202e\u2066-\u2069]")


# --- Prompt injection patterns ---
# Tuned to catch real attacks, not legitimate conversation about these topics.
# Each tuple: (compiled_regex, label, weight)

_INJECTION_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    # Direct instruction override attempts
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|context)",
                re.IGNORECASE), "instruction_override", 0.6),
    (re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
                re.IGNORECASE), "instruction_override", 0.6),
    (re.compile(r"forget\s+(everything|all)\s+(you('ve| have)\s+been\s+told|above|previous)",
                re.IGNORECASE), "instruction_override", 0.5),
    (re.compile(r"you\s+are\s+now\s+(a|an|in)\s+", re.IGNORECASE), "role_hijack", 0.3),
    (re.compile(r"act\s+as\s+if\s+you\s+(have\s+)?no\s+(restrictions?|rules?|guardrails?)",
                re.IGNORECASE), "role_hijack", 0.5),
    (re.compile(r"pretend\s+(you('re| are)\s+)?(a\s+)?(different|new|unrestricted)",
                re.IGNORECASE), "role_hijack", 0.3),

    # Fake system/instruction markers injected in user content
    (re.compile(r"^(system|SYSTEM)\s*:", re.MULTILINE), "fake_system_prefix", 0.5),
    (re.compile(r"###\s*(Instruction|System|INST|Response)", re.IGNORECASE), "fake_delimiter", 0.5),
    (re.compile(r"\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>", re.IGNORECASE),
     "chat_template_injection", 0.7),
    (re.compile(r"<\|system\|>|<\|user\|>|<\|assistant\|>"), "chat_template_injection", 0.7),
    (re.compile(r"BEGIN\s+(SYSTEM\s+)?PROMPT|END\s+(SYSTEM\s+)?PROMPT",
                re.IGNORECASE), "fake_delimiter", 0.4),

    # Prompt leaking attempts
    (re.compile(r"(repeat|show|print|output|reveal|display)\s+(your|the|full|entire|original)\s+"
                r"(system\s+)?(prompt|instructions?|rules?|guidelines?)",
                re.IGNORECASE), "prompt_leak", 0.4),
    (re.compile(r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
                re.IGNORECASE), "prompt_leak", 0.2),
]


# --- Data exfiltration patterns ---

_EXFIL_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    # Accessing sensitive system paths
    (re.compile(r"/etc/passwd|/etc/shadow|/etc/sudoers"), "sensitive_path", 0.6),
    (re.compile(r"~/\.ssh/|/\.ssh/|id_rsa|id_ed25519|authorized_keys"), "ssh_key_access", 0.7),
    (re.compile(r"~/\.env\b|/\.env\b|\.env\.local|\.env\.production"), "env_file_access", 0.5),
    (re.compile(r"\bAPI_KEY\b|\bSECRET_KEY\b|\bPRIVATE_KEY\b|\bAWS_SECRET",
                re.IGNORECASE), "credential_reference", 0.3),

    # URL with encoded data (potential exfiltration channel)
    (re.compile(r"https?://[^\s]+\?[^\s]*(?:data|payload|exfil|token)=[^\s]{50,}",
                re.IGNORECASE), "url_data_exfil", 0.5),

    # Base64 blobs (>100 chars of base64 is suspicious in chat)
    (re.compile(r"[A-Za-z0-9+/]{100,}={0,2}"), "base64_blob", 0.3),

    # Env var dumping
    (re.compile(r"(print|echo|cat|dump)\s+.{0,20}(environ|env\b|os\.environ)",
                re.IGNORECASE), "env_dump", 0.5),
]


# --- Command injection patterns (for tool inputs) ---

_CMD_INJECTION_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    # Shell metacharacters that chain commands
    (re.compile(r";\s*\w"), "semicolon_chain", 0.4),
    (re.compile(r"\|\s*\w"), "pipe_chain", 0.2),
    (re.compile(r"\$\("), "command_substitution", 0.5),
    (re.compile(r"`[^`]+`"), "backtick_execution", 0.5),
    (re.compile(r"&&\s*\w"), "and_chain", 0.3),
    (re.compile(r"\|\|\s*\w"), "or_chain", 0.3),

    # Common injection payloads
    (re.compile(r";\s*(curl|wget|nc|ncat|bash|sh|python)\b"), "shell_injection", 0.8),
    (re.compile(r"\|\s*(bash|sh|python|perl|ruby)\b"), "pipe_to_shell", 0.8),
    (re.compile(r">(>)?\s*/"), "redirect_to_root", 0.7),
]


# --- Output scanning patterns (data leakage from assistant responses) ---

_OUTPUT_LEAK_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    # Private key material
    (re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"), "private_key_leak", 0.9),
    (re.compile(r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----"), "private_key_leak", 0.9),

    # API keys / tokens (common formats)
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "api_key_leak", 0.7),
    (re.compile(r"ghp_[a-zA-Z0-9]{36,}"), "github_token_leak", 0.7),
    (re.compile(r"glpat-[a-zA-Z0-9\-]{20,}"), "gitlab_token_leak", 0.7),
    (re.compile(r"xox[bpras]-[a-zA-Z0-9\-]{10,}"), "slack_token_leak", 0.7),

    # Password hashes
    (re.compile(r"\$[126aby]\$[^\s]{20,}"), "password_hash_leak", 0.6),

    # Large base64 blobs in output (potential data exfiltration)
    (re.compile(r"[A-Za-z0-9+/]{200,}={0,2}"), "base64_exfil", 0.4),
]


def _scan_patterns(
    text: str,
    patterns: list[tuple[re.Pattern, str, float]],
) -> tuple[float, list[str]]:
    """Scan text against a list of patterns. Returns (risk_score, warnings)."""
    score = 0.0
    warnings: list[str] = []
    for regex, label, weight in patterns:
        match = regex.search(text)
        if match:
            snippet = match.group()[:80]
            warnings.append(f"{label}({weight:.1f}): '{snippet}'")
            score += weight
    return min(score, 1.0), warnings


def _check_invisible_chars(text: str) -> tuple[float, list[str]]:
    """Check for invisible Unicode characters and RTL overrides."""
    score = 0.0
    warnings: list[str] = []

    invisible_count = len(_INVISIBLE_CHARS.findall(text))
    if invisible_count > 0:
        score += min(0.3 + invisible_count * 0.05, 0.6)
        warnings.append(f"invisible_unicode({score:.1f}): {invisible_count} chars found")

    rtl_count = len(_RTL_OVERRIDES.findall(text))
    if rtl_count > 0:
        rtl_score = min(0.2 + rtl_count * 0.1, 0.5)
        score += rtl_score
        warnings.append(f"rtl_override({rtl_score:.1f}): {rtl_count} chars found")

    return min(score, 1.0), warnings


def _strip_invisible(text: str) -> str:
    """Remove invisible characters that serve no legitimate purpose."""
    text = _INVISIBLE_CHARS.sub("", text)
    text = _RTL_OVERRIDES.sub("", text)
    return text


def _check_homoglyphs(text: str) -> tuple[float, list[str]]:
    """Detect mixed-script homoglyph attacks (e.g., Cyrillic 'а' for Latin 'a').

    Only flags when multiple scripts are mixed in ways that suggest obfuscation,
    not legitimate multilingual text.
    """
    if not text or len(text) < 10:
        return 0.0, []

    # Count characters per script category (only for letter chars)
    scripts: dict[str, int] = {}
    for ch in text:
        if unicodedata.category(ch).startswith("L"):
            # Use the Unicode block name as a rough script indicator
            try:
                name = unicodedata.name(ch, "")
            except ValueError:
                continue
            if "CYRILLIC" in name:
                scripts["CYRILLIC"] = scripts.get("CYRILLIC", 0) + 1
            elif "GREEK" in name:
                scripts["GREEK"] = scripts.get("GREEK", 0) + 1
            elif "LATIN" in name:
                scripts["LATIN"] = scripts.get("LATIN", 0) + 1

    # Flag if Latin is mixed with Cyrillic or Greek (common homoglyph attack)
    warnings: list[str] = []
    score = 0.0
    if "LATIN" in scripts:
        for suspect in ("CYRILLIC", "GREEK"):
            if suspect in scripts and scripts[suspect] <= scripts["LATIN"] * 0.3:
                # Small number of foreign chars mixed into Latin = suspicious
                score += 0.4
                warnings.append(
                    f"homoglyph_mix(0.4): {scripts[suspect]} {suspect} chars "
                    f"mixed with {scripts['LATIN']} LATIN chars"
                )

    return min(score, 1.0), warnings


def sanitize_input(text: str) -> tuple[str, float, list[str]]:
    """Scan and sanitize user input for injection attacks.

    Returns:
        (cleaned_text, risk_score, warnings)
        - cleaned_text: input with invisible chars stripped
        - risk_score: 0.0-1.0 (above 0.7 = should block)
        - warnings: list of detection descriptions
    """
    if not text:
        return text, 0.0, []

    total_score = 0.0
    all_warnings: list[str] = []

    # 1. Invisible Unicode
    inv_score, inv_warns = _check_invisible_chars(text)
    total_score += inv_score
    all_warnings.extend(inv_warns)

    # 2. Homoglyphs
    hom_score, hom_warns = _check_homoglyphs(text)
    total_score += hom_score
    all_warnings.extend(hom_warns)

    # 3. Prompt injection patterns
    inj_score, inj_warns = _scan_patterns(text, _INJECTION_PATTERNS)
    total_score += inj_score
    all_warnings.extend(inj_warns)

    # 4. Data exfiltration patterns
    exf_score, exf_warns = _scan_patterns(text, _EXFIL_PATTERNS)
    total_score += exf_score
    all_warnings.extend(exf_warns)

    # 5. Command injection patterns
    cmd_score, cmd_warns = _scan_patterns(text, _CMD_INJECTION_PATTERNS)
    total_score += cmd_score
    all_warnings.extend(cmd_warns)

    # Clamp to 1.0
    total_score = min(total_score, 1.0)

    # Strip invisible chars from the text (always, regardless of score)
    cleaned = _strip_invisible(text)

    # Log detections
    if all_warnings:
        level = logging.WARNING if total_score >= 0.7 else logging.INFO
        logger.log(
            level,
            "input_scan score=%.2f warnings=%d details=[%s] input_preview='%s'",
            total_score,
            len(all_warnings),
            "; ".join(all_warnings),
            text[:100].replace("\n", "\\n"),
        )

    return cleaned, total_score, all_warnings


def check_output(text: str) -> tuple[str, float, list[str]]:
    """Scan assistant output for data leakage.

    Returns:
        (text, risk_score, warnings)
        - text: unchanged (we don't modify output, just flag it)
        - risk_score: 0.0-1.0 (above 0.7 = should block)
        - warnings: list of detection descriptions
    """
    if not text:
        return text, 0.0, []

    score, warnings = _scan_patterns(text, _OUTPUT_LEAK_PATTERNS)

    if warnings:
        level = logging.WARNING if score >= 0.7 else logging.INFO
        logger.log(
            level,
            "output_scan score=%.2f warnings=%d details=[%s] output_preview='%s'",
            score,
            len(warnings),
            "; ".join(warnings),
            text[:100].replace("\n", "\\n"),
        )

    return text, score, warnings


# --- Refusal response ---

REFUSAL_RESPONSE = (
    "I can't process this request — it was flagged by the input guard. "
    "If this is a false positive, please rephrase your message."
)

OUTPUT_REDACTED_RESPONSE = (
    "The response was redacted because it contained potentially sensitive data "
    "(private keys, API tokens, or credentials). This is a safety measure."
)
