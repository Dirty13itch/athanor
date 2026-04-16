The repos in ~/repos/reference/ are READ-ONLY parts warehouses. Never commit to them.

When porting code from a reference repo:
- Read the source thoroughly before writing anything
- Adapt to Athanor's patterns, don't transplant Hydra/Kaizen patterns
- Athanor uses: async/await, LiteLLM for inference, Redis for state, Qdrant for vectors, Ansible for deployment
- Hydra used: TabbyAPI/ExLlamaV2, NixOS, Docker Compose, CrewAI
- Kaizen used: SGLang, Kubernetes/Talos, GWT salience competition
- The interfaces differ but the logic is often portable. Extract the algorithm, rewrite the glue.
