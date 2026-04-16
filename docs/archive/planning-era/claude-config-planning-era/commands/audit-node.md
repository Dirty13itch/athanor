SSH into $NODE and report:
1. GPU status (nvidia-smi)
2. Running vLLM processes (ps aux | grep vllm)
3. Disk usage on model directories (du -sh ~/models/*)
4. Memory usage (free -h)
5. Active systemd services related to Athanor (systemctl list-units | grep -E "vllm|litellm|qdrant|neo4j|redis")
6. Network connectivity to other nodes (ping -c1 foundry workshop vault dev)
7. Current vLLM serve command line args from process list

Format as a concise status report. Flag anything abnormal.
