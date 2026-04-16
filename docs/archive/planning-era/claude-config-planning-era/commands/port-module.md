Port the Hydra module at reference/hydra/src/hydra_tools/$MODULE into the Athanor codebase.

Steps:
1. Read the source file completely. Understand its purpose, dependencies, and interfaces.
2. Read the equivalent area in athanor/ to understand where it integrates.
3. Identify import differences (hydra used different package structure).
4. Identify service differences (hydra used TabbyAPI/ExLlamaV2, Athanor uses vLLM/LiteLLM).
5. Write the adapted module into the correct location in athanor/.
6. Write or update tests in athanor/tests/.
7. Run ruff check and ruff format on the new files.
8. Run pytest on the new tests.
9. If tests pass, git add and commit with message "port: $MODULE from hydra reference".
10. If tests fail, fix and retry.

Do NOT copy code blindly. Adapt to Athanor's patterns: async-first, LiteLLM for inference calls, Redis for state, Qdrant for vectors.
