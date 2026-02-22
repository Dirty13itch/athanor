#!/bin/bash
# TP Scaling Benchmark - Does tensor parallelism actually help?
# Run this on Node 1 BEFORE rack session to validate pooling strategy

MODEL="/models/Qwen3-32B-AWQ"
RESULTS="/tmp/tp-benchmark-$(date +%Y%m%d-%H%M%S).txt"

echo "TP Scaling Benchmark - Qwen3-32B-AWQ" | tee "$RESULTS"
echo "========================================" | tee -a "$RESULTS"
echo "" | tee -a "$RESULTS"

# Test 1: TP=1 (single GPU baseline)
echo "Test 1: TP=1 (Single GPU - RTX 5070 Ti)" | tee -a "$RESULTS"
docker run --rm --gpus '"device=0"' \
  --shm-size=8g \
  nvcr.io/nvidia/vllm:25.12-py3 \
  vllm serve "$MODEL" \
  --quantization awq \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 32 \
  --port 8001 &
PID1=$!
sleep 60  # Wait for model load

# Run benchmark requests
python3 << 'PYTHON'
import requests, time, json

url = "http://localhost:8001/v1/completions"
prompt = "Explain the theory of relativity in detail, covering both special and general relativity."

times = []
for i in range(10):
    start = time.time()
    resp = requests.post(url, json={
        "model": "/models/Qwen3-32B-AWQ",
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0
    })
    elapsed = time.time() - start
    tokens = resp.json().get('usage', {}).get('completion_tokens', 0)
    tok_per_sec = tokens / elapsed if elapsed > 0 else 0
    times.append(tok_per_sec)
    print(f"Request {i+1}: {tok_per_sec:.1f} tok/s")

avg = sum(times) / len(times)
print(f"\nTP=1 Average: {avg:.1f} tok/s")
with open("/tmp/tp1-result.txt", "w") as f:
    f.write(f"{avg:.1f}")
PYTHON

kill $PID1
echo "" | tee -a "$RESULTS"

# Test 2: TP=2 (two GPUs)
echo "Test 2: TP=2 (Two GPUs)" | tee -a "$RESULTS"
docker run --rm --gpus '"device=0,1"' \
  --shm-size=16g \
  nvcr.io/nvidia/vllm:25.12-py3 \
  vllm serve "$MODEL" \
  --quantization awq \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 64 \
  --port 8002 &
PID2=$!
sleep 90  # Wait for model load

python3 << 'PYTHON'
import requests, time

url = "http://localhost:8002/v1/completions"
prompt = "Explain the theory of relativity in detail, covering both special and general relativity."

times = []
for i in range(10):
    start = time.time()
    resp = requests.post(url, json={
        "model": "/models/Qwen3-32B-AWQ",
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0
    })
    elapsed = time.time() - start
    tokens = resp.json().get('usage', {}).get('completion_tokens', 0)
    tok_per_sec = tokens / elapsed if elapsed > 0 else 0
    times.append(tok_per_sec)
    print(f"Request {i+1}: {tok_per_sec:.1f} tok/s")

avg = sum(times) / len(times)
print(f"\nTP=2 Average: {avg:.1f} tok/s")
with open("/tmp/tp2-result.txt", "w") as f:
    f.write(f"{avg:.1f}")
PYTHON

kill $PID2
echo "" | tee -a "$RESULTS"

# Test 3: TP=4 (four GPUs)
echo "Test 3: TP=4 (Four GPUs)" | tee -a "$RESULTS"
docker run --rm --gpus '"device=0,1,2,3"' \
  --shm-size=32g \
  nvcr.io/nvidia/vllm:25.12-py3 \
  vllm serve "$MODEL" \
  --quantization awq \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 128 \
  --port 8003 &
PID3=$!
sleep 120  # Wait for model load

python3 << 'PYTHON'
import requests, time

url = "http://localhost:8003/v1/completions"
prompt = "Explain the theory of relativity in detail, covering both special and general relativity."

times = []
for i in range(10):
    start = time.time()
    resp = requests.post(url, json={
        "model": "/models/Qwen3-32B-AWQ",
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0
    })
    elapsed = time.time() - start
    tokens = resp.json().get('usage', {}).get('completion_tokens', 0)
    tok_per_sec = tokens / elapsed if elapsed > 0 else 0
    times.append(tok_per_sec)
    print(f"Request {i+1}: {tok_per_sec:.1f} tok/s")

avg = sum(times) / len(times)
print(f"\nTP=4 Average: {avg:.1f} tok/s")
with open("/tmp/tp4-result.txt", "w") as f:
    f.write(f"{avg:.1f}")
PYTHON

kill $PID3
echo "" | tee -a "$RESULTS"

# Summary
echo "========================================" | tee -a "$RESULTS"
TP1=$(cat /tmp/tp1-result.txt)
TP2=$(cat /tmp/tp2-result.txt)
TP4=$(cat /tmp/tp4-result.txt)

echo "RESULTS:" | tee -a "$RESULTS"
echo "  TP=1: $TP1 tok/s" | tee -a "$RESULTS"
echo "  TP=2: $TP2 tok/s" | tee -a "$RESULTS"
echo "  TP=4: $TP4 tok/s" | tee -a "$RESULTS"
echo "" | tee -a "$RESULTS"
echo "Full results saved to: $RESULTS"

# Decision logic
python3 << PYTHON
tp1 = float("$TP1")
tp4 = float("$TP4")

if tp4 > tp1 * 0.8:  # If TP=4 is within 20% of TP=1
    print("\n✓ RECOMMENDATION: TP=4 pooling is viable")
    print("  Proceed with 7-GPU configuration for maximum VRAM pooling")
else:
    print("\n✗ WARNING: TP=4 overhead is significant")
    print("  Consider distributed serving instead of pooling")
PYTHON
