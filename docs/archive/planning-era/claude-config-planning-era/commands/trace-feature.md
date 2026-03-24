Trace the feature "$FEATURE" across all repos in ~/repos/reference/ and the live athanor/ repo.

For each repo that has this feature:
1. Find the relevant source files (grep -r for function names, class names, config keys)
2. Read the implementation
3. Note the approach, dependencies, and design decisions
4. Note what worked and what was abandoned (check git log for relevant commits)

Then produce:
- A comparison table: repo | approach | status | dependencies | notes
- The strongest implementation (most complete, best tested, cleanest code)
- A recommendation for how to bring this into athanor/ with minimal adaptation
- Specific files to copy or adapt, with the changes needed
