Test the inference endpoint at $ENDPOINT (e.g., http://foundry:8000, http://workshop:8100, http://vault:4000).

Run these 5 checks:
1. Health: GET /health or /v1/models — confirm the service is alive
2. Completion: POST a simple "What is 2+2?" — confirm coherent response
3. Tool call: POST with a dummy get_weather tool — confirm structured function_call output
4. Thinking mode: POST with "Think step by step: what is 15% of 340?" — confirm reasoning trace
5. Latency: Time each request, report TTFT and total latency

For LiteLLM (:4000), also test tag routing:
- Send with tags: ["coordinator"] — should route to FOUNDRY
- Send with tags: ["worker"] — should route to WORKSHOP
- Send with tags: ["utility"] — should route to 4090

Report pass/fail for each check with latency numbers. Flag any unexpected behavior.
