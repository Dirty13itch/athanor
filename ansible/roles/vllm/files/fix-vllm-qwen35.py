#!/usr/bin/env python3
"""
Patch vLLM for Qwen3.5 DeltaNet support.

Applied conditionally — safe to re-run (idempotent).

1. RMSNormGated missing activation attribute (vLLM PR #35423)
   Qwen3.5 DeltaNet layers pass activation= to CUDA normalization kernels.
   Fix: Ensure self.activation = "swish" exists in RMSNormGated.__init__.

2. transformers rope_utils list|set type error
   ignore_keys_at_rope_validation is a list but used with | (set union).
   Fix: Wrap in set() before | operation.

Remove this script once vLLM stable includes both fixes (expected v0.17.0+).
"""

import re
import sys


def find_module_file(module_path: str) -> str | None:
    """Find the source file for a Python module path."""
    try:
        parts = module_path.rsplit(".", 1)
        pkg = __import__(parts[0], fromlist=[parts[1]] if len(parts) > 1 else [])
        mod = getattr(pkg, parts[1]) if len(parts) > 1 else pkg
        return mod.__file__
    except (ImportError, AttributeError):
        return None


def patch_rmsnorm_gated() -> bool:
    """Add self.activation = 'swish' to RMSNormGated if missing."""
    try:
        import vllm.model_executor.layers.layernorm as mod

        path = mod.__file__
    except ImportError:
        print("SKIP: vllm.model_executor.layers.layernorm not found")
        return True

    with open(path) as f:
        content = f.read()

    # Check if already patched
    if "self.activation" in content:
        print(f"SKIP: RMSNormGated already has self.activation in {path}")
        return True

    if "class RMSNormGated" not in content:
        print(f"SKIP: RMSNormGated class not found in {path}")
        return True

    # Find the __init__ method body and add activation after the last
    # self.xxx = line before reset_parameters or a method definition.
    # Strategy: insert after self.norm_before_gate or self.eps assignment.
    for anchor in [
        "self.norm_before_gate = norm_before_gate",
        "self.norm_before_gate",
        "self.group_size",
        "self.eps = eps",
        "self.variance_epsilon",
    ]:
        if anchor in content:
            new_content = content.replace(
                anchor,
                f'{anchor}\n        self.activation = "swish"  # PR #35423 fix',
            )
            with open(path, "w") as f:
                f.write(new_content)
            print(f"PATCHED: RMSNormGated.activation in {path}")
            return True

    print(f"WARN: Could not find insertion point in {path}")
    return False


def patch_rope_utils() -> bool:
    """Fix list|set type error in transformers rope_utils."""
    try:
        import transformers.modeling_rope_utils as mod

        path = mod.__file__
    except ImportError:
        print("SKIP: transformers.modeling_rope_utils not found")
        return True

    with open(path) as f:
        content = f.read()

    # Check if already fixed
    if "set(ignore_keys_at_rope_validation)" in content:
        print(f"SKIP: rope_utils already uses set() in {path}")
        return True

    # The buggy pattern: list | set fails in Python
    old = 'ignore_keys_at_rope_validation | {"partial_rotary_factor"}'
    if old not in content:
        print(f"SKIP: rope_utils pattern not found (already fixed or different version)")
        return True

    new = 'set(ignore_keys_at_rope_validation) | {"partial_rotary_factor"}'
    new_content = content.replace(old, new)

    with open(path, "w") as f:
        f.write(new_content)
    print(f"PATCHED: rope_utils set() fix in {path}")
    return True


if __name__ == "__main__":
    ok = True
    ok = patch_rmsnorm_gated() and ok
    ok = patch_rope_utils() and ok
    if not ok:
        print("ERROR: One or more patches failed")
        sys.exit(1)
    print("All patches applied successfully")
