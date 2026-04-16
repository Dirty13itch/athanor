# Voice Interaction for Athanor

**Date:** 2026-02-24
**Status:** Complete -- recommendation ready
**Supports:** Build Manifest 6.3 (Voice Interaction)
**Depends on:** ADR-010 (Home Automation), ADR-018 (GPU Orchestration), ADR-012 (LiteLLM Routing)

---

## Context

Athanor currently has text-only interaction: browser chat via Open WebUI (Node 2:3000), agent API (Node 1:9000), and Claude Code terminal. Voice adds a natural interaction layer, especially for hands-free home control and ambient queries.

The system has 7 GPUs across 2 nodes. GPU 4 on Node 1 (5070 Ti, 16 GB) runs only a 0.6 GB embedding model, wasting ~14.8 GB VRAM. This is the obvious home for voice workloads. Home Assistant on VAULT already supports the Wyoming voice protocol.

Requirements:
- Local/private (no cloud STT/TTS)
- Low latency (<2s end-to-end for simple queries)
- Works with existing agent server (OpenAI-compatible API)
- Home Assistant integration via Wyoming protocol
- Docker-deployed, single-person maintainable
- Runs on a 16 GB GPU (5070 Ti or 5060 Ti)

---

## 1. Speech-to-Text (STT)

### Options Evaluated

| Engine | Architecture | Model Sizes | VRAM (large model) | Speed vs Whisper | Accuracy (WER) | Streaming | GPU Support |
|--------|-------------|-------------|--------------------|--------------------|-----------------|-----------|-------------|
| **faster-whisper** | CTranslate2 (C++) | tiny to large-v3 | ~2 GB (int8), ~4.5 GB (fp16) | 4x faster | Same as Whisper | Yes (batched) | CUDA 12 + cuBLAS |
| **whisper.cpp** | GGML (C/C++) | tiny to large | ~3.9 GB (large, RAM) | 2-3x faster | Same as Whisper | Yes (real-time SDL2) | CUDA, Vulkan, Metal |
| **distil-whisper** | Distilled Whisper | 166M - 756M params | ~1.5 GB (distil-large-v3, fp16) | 6x faster | +1.3% WER vs large-v3 | Via faster-whisper | Via faster-whisper |
| **Whisper (original)** | PyTorch | tiny to large-v3 | ~5 GB (large-v3, fp16) | Baseline | 8.4% short-form | No native | CUDA |

### Analysis

**faster-whisper** is the clear winner for server deployment. It wraps Whisper models in CTranslate2, achieving 4x speedup with lower VRAM usage. The large-v3 model in int8 uses ~2 GB VRAM. Combined with distil-whisper models (distil-large-v3 available through faster-whisper), you get 6x speed with negligible accuracy loss.

**Benchmark data** (RTX 3070 Ti, 13 min audio):
- OpenAI Whisper large-v2: 2m23s, 4,708 MB
- faster-whisper large-v2 (fp16): 1m03s, 4,525 MB
- faster-whisper large-v2 (int8, batched): 17s, ~2,500 MB

**distil-whisper** models are the sweet spot. `distil-large-v3` has 756M parameters (vs 1,550M for full large-v3), runs 6x faster, and scores 10.8% long-form WER vs 11.0% for the full model. Barely any quality loss.

**whisper.cpp** excels on edge devices and CPU-only scenarios but offers less advantage on GPU-equipped servers where CTranslate2 already optimizes well.

**VRAM impact on 16 GB GPU:** faster-whisper with distil-large-v3 in int8 uses approximately 1-2 GB VRAM. This can trivially coexist with the embedding model (0.6 GB) on GPU 4. Total: ~2.5 GB of 16 GB used.

### STT Recommendation

**faster-whisper with distil-large-v3 (int8)**. ~1.5 GB VRAM, 6x faster than Whisper, near-identical accuracy. Deploy via Wyoming wrapper for HA integration.

---

## 2. Text-to-Speech (TTS)

### Options Evaluated

| Engine | Params | VRAM | Quality | Latency | Voice Cloning | Streaming | Languages | License |
|--------|--------|------|---------|---------|---------------|-----------|-----------|---------|
| **Kokoro-82M** | 82M | <1 GB | Excellent (TTS Arena #1) | <100ms RTF | No (54 preset voices) | Yes | 8 languages | Apache 2.0 |
| **Piper** | ~20M | 0 (CPU) | Good (natural) | ~50ms RTF | No (100+ voices) | No | 30+ languages | MIT/GPL |
| **Coqui XTTS v2** | ~500M | ~4 GB | Excellent | <200ms streaming | Yes (6-30s sample) | Yes | 16 languages | Coqui Public (archived) |
| **Fish Speech (S1-mini)** | 500M | ~2-3 GB | Excellent (Arena #1 full) | 1:7 RTF (4090) | Yes (10-30s sample) | Yes | 13 languages | CC-BY-NC-SA 4.0 |
| **F5-TTS** | ~300M | ~2-3 GB | Very good | 253ms avg | Yes (ref audio) | Yes (chunked) | EN/ZH | CC-BY-NC (model) |
| **Bark** | ~1B | ~12 GB | Good (generative) | Near real-time | No (100 presets) | No | 12 languages | MIT |
| **CSM (Sesame)** | 1B | ~4-6 GB | Very good | Unknown | No | No | English only | Apache 2.0 |

### Analysis

**Kokoro-82M** is the standout for this use case. At only 82M parameters, it uses negligible VRAM (<1 GB), generates speech faster than real-time, and ranked #1 on TTS Arena. Apache 2.0 license. 54 voices across 8 languages. The only downside: no voice cloning. For a voice assistant where you pick a consistent voice, this is irrelevant.

**Piper** is the battle-tested choice for Home Assistant. Runs on CPU only (zero VRAM), 100+ voices, Wyoming protocol integration already built. Quality is good but a tier below Kokoro and XTTS. The project has moved to OHF-Voice/piper1-gpl but remains actively maintained. It is the default recommendation in all HA voice documentation.

**Coqui XTTS v2** offers the best voice cloning but the project is archived (Coqui shut down). Still functional but no future updates. 4 GB VRAM. Good streaming latency (<200ms). Worth considering if voice cloning becomes important.

**Fish Speech S1-mini** is competitive on quality (S1 full model is TTS Arena #1) but the NC license restricts commercial use, and 500M params require more VRAM. The full S1 model (4B params) is impractical for a 16 GB card.

**Bark** is too slow and VRAM-hungry (12 GB) for real-time voice assistant use. Better suited for offline audio generation.

**CSM (Sesame)** is interesting but English-only, no streaming, and limited documentation. Too early.

### TTS Recommendation

**Two-tier approach:**
1. **Piper** for Wyoming/Home Assistant voice pipeline (CPU-only, zero GPU cost, proven HA integration)
2. **Kokoro-82M** for higher-quality agent responses via API (<1 GB VRAM, faster than real-time, Apache licensed)

This gives HA voice satellites the lightweight Piper path, while browser/API interactions get Kokoro quality.

---

## 3. Wake Word Detection

### Options Evaluated

| Engine | Architecture | CPU Usage | Custom Words | Accuracy | HA Integration | License |
|--------|-------------|-----------|--------------|----------|----------------|---------|
| **openWakeWord** | ONNX + TFLite | Very low (15-20 models on RPi3 core) | Yes (Colab, <1hr) | <0.5 FA/hr, <5% FR | Wyoming server | Apache 2.0 (code), CC-BY-NC-SA (models) |
| **Porcupine** | DNN | Very low | Yes (Picovoice Console) | 11x better than PocketSphinx | No native Wyoming | Apache 2.0 |
| **Mycroft Precise** | TFLite | Low | Yes (manual training) | Good but dated | Community | Apache 2.0 |

### Analysis

**openWakeWord** is the correct choice. It has a first-party Wyoming server (`wyoming-openwakeword`), official HA add-on support, trains custom wake words in under an hour via Colab notebook, and runs 15-20 models simultaneously on a single Raspberry Pi 3 core. CPU-only. The pre-trained models include common wake words ("hey jarvis", "alexa", "ok nabu") that work out of the box.

**Porcupine** is more accurate but has no Wyoming integration and requires Picovoice Console for custom word training. Adding a Wyoming wrapper would be extra work for marginal benefit.

**Mycroft Precise** is effectively abandoned since Mycroft's shutdown.

### Wake Word Recommendation

**openWakeWord** via `wyoming-openwakeword` Docker container. CPU-only, runs on VAULT or any node. Train a custom "Hey Athanor" wake word via the Colab notebook.

---

## 4. Architecture: Wiring STT -> Agent -> TTS

### Voice Pipeline Flow

```
[Mic/Client] -> [Wake Word] -> [STT] -> [Agent Server] -> [TTS] -> [Speaker/Client]
     |              |             |            |              |           |
  Wyoming      openWakeWord  faster-whisper  Node 1:9000   Kokoro/Piper  Wyoming
  satellite      (CPU)       (GPU 4)         (existing)    (GPU 4/CPU)   satellite
```

### Two Integration Paths

#### Path A: Home Assistant Wyoming Pipeline (whole-house voice)

```
ESP32-S3 satellite (mic+speaker)
    -> Wyoming protocol over TCP
    -> HA Voice Pipeline on VAULT:8123
        -> Wake Word: wyoming-openwakeword (VAULT, CPU)
        -> STT: wyoming-faster-whisper (Node 1, GPU 4)
        -> Intent/Conversation: HA conversation agent OR custom agent
        -> TTS: wyoming-piper (VAULT, CPU)
    -> Audio back to satellite
```

HA Voice Pipeline orchestrates the entire flow. Wyoming satellites (ESP32-S3 devices, ~$13 each) in each room provide mic+speaker. HA routes wake-word-detected audio to the STT provider, gets text, processes intent, generates TTS response, and sends audio back to the satellite.

**Key limitation:** HA's built-in conversation agent handles home commands well but cannot route to Athanor's agent server natively. Two options:
1. **HA custom conversation agent** that proxies to Node 1:9000 (Python integration or REST command)
2. **HA automation** that sends transcribed text to the agent API and plays the TTS response

#### Path B: Browser/API Direct Voice (high-quality, low-latency)

```
Browser (mic via WebRTC/MediaRecorder)
    -> WebSocket to Voice Gateway service
    -> STT: faster-whisper (GPU 4)
    -> Agent API: POST Node 1:9000/v1/chat/completions
    -> TTS: Kokoro-82M (GPU 4)
    -> Audio stream back to browser via WebSocket
```

A dedicated Voice Gateway service (FastAPI + WebSocket) handles the browser-based flow. This bypasses HA entirely and connects directly to the agent server with full context (preferences, knowledge, activity history). Higher quality TTS (Kokoro vs Piper).

### Recommended: Both Paths

Path A for whole-house ambient voice via HA satellites. Path B for high-quality voice interaction via browser/dashboard. They share the same STT backend (faster-whisper on GPU 4) but diverge on TTS and orchestration.

### Voice Gateway Service (Path B)

A single FastAPI container on Node 1:

```python
# Simplified architecture
@app.websocket("/ws/voice")
async def voice_ws(ws: WebSocket):
    # 1. Receive audio chunks from browser
    audio = await receive_audio_stream(ws)

    # 2. STT: faster-whisper
    text = await stt_engine.transcribe(audio)
    await ws.send_json({"type": "transcript", "text": text})

    # 3. Agent: existing API
    response = await agent_client.chat(text, user="shaun")
    await ws.send_json({"type": "response", "text": response})

    # 4. TTS: Kokoro
    audio_stream = tts_engine.synthesize(response)
    async for chunk in audio_stream:
        await ws.send_bytes(chunk)
```

---

## 5. Home Assistant Voice Integration

### Wyoming Protocol Architecture

Wyoming is a JSONL + PCM audio peer-to-peer protocol. Services register as providers:

| Service | Wyoming Port | Docker Image | Host |
|---------|-------------|--------------|------|
| STT (faster-whisper) | 10300 | `rhasspy/wyoming-whisper` | Node 1 (GPU 4) |
| TTS (Piper) | 10200 | `rhasspy/wyoming-piper` | VAULT (CPU) |
| Wake Word (openWakeWord) | 10400 | `rhasspy/wyoming-openwakeword` | VAULT (CPU) |

### Setup Steps

1. Deploy Wyoming containers (see Section 7 below)
2. In HA: Settings > Devices & Services > Add Integration > Wyoming Protocol
3. Add each service by host:port (auto-discovery via Zeroconf also works on same subnet)
4. Configure Voice Pipeline: Settings > Voice assistants > Add assistant
   - STT: Wyoming faster-whisper
   - TTS: Wyoming Piper
   - Wake word: Wyoming openWakeWord
5. Add satellite devices (ESP32-S3 or RPi with mic/speaker)

### Conversation Agent Bridge

To route HA voice queries to Athanor's agent server instead of HA's built-in conversation agent:

**Option 1: HA REST Command + Automation**
```yaml
# configuration.yaml
rest_command:
  athanor_query:
    url: "http://192.168.1.244:9000/v1/chat/completions"
    method: POST
    headers:
      Content-Type: application/json
    payload: >
      {"model": "general-assistant",
       "messages": [{"role": "user", "content": "{{ query }}"}]}
```

**Option 2: Custom Conversation Agent (better)**
A Python-based HA custom component that implements the conversation agent interface and proxies to Node 1:9000. This makes the Athanor agent server appear as a native HA conversation provider, selectable in Voice Pipeline config.

### Satellite Hardware Options

| Device | Cost | Features | Setup |
|--------|------|----------|-------|
| M5Stack ATOM Echo | ~$13 | Mic + speaker, ESP32-S3, WiFi | ESPHome flash via browser |
| Home Assistant Voice PE | ~$59 | Better mic array, speaker, LED ring | Official, ESPHome |
| Raspberry Pi Zero 2W + ReSpeaker | ~$35 | Better audio, local wake word | wyoming-satellite (deprecated, use ESPHome) |
| Any Linux box + USB mic | $0 | Repurpose existing hardware | Wyoming satellite or Speaches |

The $13 ATOM Echo is the minimum viable satellite. The HA Voice PE ($59) has better audio quality with a proper mic array. For serious use, a Raspberry Pi with a ReSpeaker HAT gives the best audio.

---

## 6. Speaches: All-in-One Alternative

**Speaches** (formerly faster-whisper-server) deserves special attention as it unifies STT + TTS in a single OpenAI-compatible API:

| Feature | Details |
|---------|---------|
| STT engine | faster-whisper (all models) |
| TTS engines | Kokoro-82M + Piper |
| API | OpenAI-compatible (`/v1/audio/transcriptions`, `/v1/audio/speech`) |
| Streaming | SSE for STT, streaming for TTS |
| Model management | Dynamic load/unload on demand |
| Docker | `docker compose` with CUDA/CPU variants |
| License | MIT |
| Maturity | 3,000+ GitHub stars, 34 contributors, 707 commits |

### Why This Matters

Speaches provides the same `/v1/audio/speech` and `/v1/audio/transcriptions` endpoints that OpenAI uses. This means:
- Open WebUI can use it directly for voice input/output
- The agent server could add voice capabilities without custom code
- LiteLLM could potentially route audio requests to it
- Any OpenAI SDK client gets voice for free

### Speaches vs. Separate Containers

| Aspect | Speaches | Separate (wyoming-whisper + wyoming-piper) |
|--------|----------|---------------------------------------------|
| API compatibility | OpenAI-compatible | Wyoming protocol only |
| Model management | Dynamic load/unload | Static, always loaded |
| HA integration | No Wyoming (needs bridge) | Native Wyoming |
| Browser integration | Direct REST/WebSocket | Needs gateway |
| Maintenance | 1 container | 2-3 containers |
| Flexibility | Locked to supported models | Mix and match |

**Verdict:** Run both. Speaches for API/browser voice (Path B). Wyoming containers for HA voice pipeline (Path A). They can share the same GPU -- faster-whisper models are small enough.

---

## 7. Docker Deployment Plan

### Container Layout

| Container | Image | Host | Port | GPU | VRAM |
|-----------|-------|------|------|-----|------|
| `wyoming-whisper` | `rhasspy/wyoming-whisper` | Node 1 | 10300 | GPU 4 | ~1.5 GB |
| `wyoming-piper` | `rhasspy/wyoming-piper` | VAULT | 10200 | None (CPU) | 0 |
| `wyoming-openwakeword` | `rhasspy/wyoming-openwakeword` | VAULT | 10400 | None (CPU) | 0 |
| `speaches` | `speaches-ai/speaches` | Node 1 | 8200 | GPU 4 | ~1.5 GB |

### Docker Compose (Node 1 voice services)

```yaml
services:
  wyoming-whisper:
    image: rhasspy/wyoming-whisper
    ports:
      - "10300:10300"
    volumes:
      - ./data/whisper:/data
    command: >
      --model Systran/faster-distil-whisper-large-v3
      --language en
      --beam-size 1
      --device cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['4']
              capabilities: [gpu]
    restart: unless-stopped

  speaches:
    image: ghcr.io/speaches-ai/speaches:latest
    ports:
      - "8200:8000"
    volumes:
      - ./data/speaches:/root/.cache
    environment:
      - NVIDIA_VISIBLE_DEVICES=4
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['4']
              capabilities: [gpu]
    restart: unless-stopped
```

### Docker Compose (VAULT voice services)

```yaml
services:
  wyoming-piper:
    image: rhasspy/wyoming-piper
    ports:
      - "10200:10200"
    volumes:
      - ./data/piper:/data
    command: >
      --voice en_US-lessac-medium
    restart: unless-stopped

  wyoming-openwakeword:
    image: rhasspy/wyoming-openwakeword
    ports:
      - "10400:10400"
    restart: unless-stopped
```

### GPU 4 VRAM Budget (Node 1, RTX 5070 Ti, 16 GB)

| Workload | VRAM |
|----------|------|
| Qwen3-Embedding-0.6B (existing) | ~1.2 GB |
| faster-whisper distil-large-v3 (int8) | ~1.5 GB |
| Kokoro-82M (via Speaches) | <1 GB |
| CUDA overhead | ~0.5 GB |
| **Total** | **~4.2 GB** |
| **Remaining** | **~11.8 GB** |

This leaves substantial headroom. GPU 4 can comfortably run embedding + STT + TTS simultaneously, with room left for future workloads.

---

## 8. Latency Budget

### Target: <2 seconds end-to-end for simple queries

For a responsive voice assistant, the perception thresholds are:
- **<500ms**: Feels instant (like talking to a person)
- **500ms-1s**: Noticeable but acceptable
- **1-2s**: Feels like the system is "thinking" (tolerable for complex queries)
- **>2s**: Feels broken for simple commands, acceptable for research queries
- **>5s**: Unacceptable for any interactive use

### Latency Breakdown (estimated for Athanor hardware)

| Stage | Duration | Notes |
|-------|----------|-------|
| Wake word detection | ~80ms | openWakeWord processes 80ms frames |
| Audio capture + VAD | 200-500ms | Wait for speech end detection |
| Network (satellite -> Node 1) | <5ms | 5GbE LAN |
| **STT** (faster-whisper distil-large-v3) | **100-300ms** | Short utterance on RTX 5070 Ti |
| Network (Node 1 internal) | <1ms | Same machine |
| **LLM inference** (first token) | **200-500ms** | Qwen3-32B-AWQ on TP=4, depends on prompt length |
| **LLM inference** (full response) | **500-2000ms** | ~50-100 tok/s, short response = 20-40 tokens |
| **TTS** (Kokoro/Piper) | **100-300ms** | Faster than real-time synthesis |
| Network (Node 1 -> satellite) | <5ms | 5GbE LAN |
| Audio playback start | <50ms | Buffer first chunk |
| **Total (simple query)** | **~1.2-1.7s** | From end of speech to start of audio response |
| **Total (complex query)** | **~2-4s** | Longer LLM generation |

### Optimization Strategies

1. **Streaming TTS**: Start TTS as soon as the first sentence of LLM output is complete, don't wait for full response. This overlaps LLM generation with TTS + playback.
2. **Streaming STT**: Begin transcription while user is still speaking (faster-whisper supports this).
3. **beam_size=1**: For real-time STT, beam_size=1 gives faster results with minimal accuracy loss.
4. **Short system prompts**: Minimize agent system prompt length for voice interactions to reduce time-to-first-token.
5. **GPU co-location**: STT + TTS on the same GPU (GPU 4) avoids network hops.
6. **vLLM continuous batching**: Already handles concurrent requests efficiently.

### With Streaming Optimization

```
User finishes speaking
  |-- 100-300ms STT --|
                      |-- 200-500ms LLM TTFT --|
                                                |-- TTS 1st sentence ~100ms --|
                                                                              |-- Audio plays --|
                                                |-- LLM continues generating --|-- TTS streams--|

Total to first audio: ~400-900ms (with streaming)
```

Streaming drops perceived latency to under 1 second for simple queries. The user hears the response begin while the LLM is still generating the rest.

---

## 9. Blackwell GPU Compatibility Note

The RTX 5070 Ti and 5060 Ti use Blackwell architecture (sm_120). The standard `rhasspy/wyoming-whisper` Docker image uses CTranslate2 which depends on CUDA + cuBLAS. This should work with CUDA 12.x on Blackwell, but needs verification.

**Risk mitigation:**
- Test the standard Docker image first
- If CTranslate2 has sm_120 issues (similar to the AWQ Marlin kernel problem documented in CLAUDE.md), fall back to whisper.cpp with CUDA backend or build CTranslate2 from source against CUDA 12.8+
- Speaches bundles its own faster-whisper and may have fresher CUDA support

The Piper and openWakeWord containers run on CPU, so GPU compatibility is not a concern for those.

---

## 10. Summary Comparison: All-in-One Solutions

| Solution | Components | Containers | HA Integration | OpenAI API | Maintenance |
|----------|-----------|------------|----------------|------------|-------------|
| **Wyoming stack** | whisper + piper + openwakeword | 3 on VAULT/Node 1 | Native | No | Low (proven) |
| **Speaches** | faster-whisper + Kokoro/Piper | 1 on Node 1 | No Wyoming | Yes | Low (unified) |
| **openedai-speech** | Piper (tts-1) + XTTS (tts-1-hd) | 1 | No | Yes (speech only) | Low |
| **Wyoming + Speaches** | Both stacks | 4 total | Native | Yes | Medium |

---

## Recommendation

### Phase 1: Wyoming Stack for Home Assistant (minimal, proven)

Deploy three containers:
1. `wyoming-faster-whisper` on Node 1 (GPU 4) -- port 10300
2. `wyoming-piper` on VAULT (CPU) -- port 10200
3. `wyoming-openwakeword` on VAULT (CPU) -- port 10400

Configure HA Voice Pipeline. Buy 1-2 M5Stack ATOM Echo satellites ($13 each). Get whole-house voice working with HA's native conversation agent first.

**Effort:** ~2 hours deploy + configure.
**VRAM cost:** ~1.5 GB on GPU 4 (from 1.2 GB current to ~2.7 GB total).

### Phase 2: Speaches for API/Browser Voice

Deploy Speaches on Node 1 (GPU 4) -- port 8200. This gives OpenAI-compatible STT+TTS API. Wire into Open WebUI for voice chat. Add WebSocket voice endpoint to agent server.

**Effort:** ~1 hour deploy, ~4 hours for agent server voice integration.
**VRAM cost:** Shared with Phase 1 models (dynamic load/unload).

### Phase 3: Agent Bridge for HA

Build a custom HA conversation agent component or REST automation that routes HA voice queries to Node 1:9000 instead of HA's built-in intent handler. This gives the full Athanor agent experience through HA voice satellites.

**Effort:** ~4-8 hours (custom HA component).

### Phase 4: Custom Wake Word

Train "Hey Athanor" wake word using openWakeWord's Colab notebook. Deploy to wyoming-openwakeword as custom model.

**Effort:** ~2 hours.

---

## Open Questions

1. **Blackwell CTranslate2 compatibility**: Does faster-whisper's CTranslate2 backend work on sm_120 GPUs out of the box? Needs testing.
2. **Speaches + Wyoming bridge**: Can Speaches expose a Wyoming interface, or would we need a thin bridge service? The two protocols (OpenAI REST vs Wyoming JSONL+PCM) are different.
3. **HA conversation agent routing**: The cleanest path to routing HA voice to Athanor agents needs prototyping. REST command is quick but loses context; custom component is better but more work.
4. **Audio quality of $13 satellite**: The ATOM Echo has a tiny speaker. For rooms where audio quality matters, the HA Voice PE ($59) or a Pi + speaker might be necessary.

---

## Sources

### STT
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper) -- CTranslate2 Whisper implementation, benchmarks
- [whisper.cpp GitHub](https://github.com/ggerganov/whisper.cpp) -- GGML Whisper, model sizes, acceleration
- [distil-whisper GitHub](https://github.com/huggingface/distil-whisper) -- Distilled models, WER data, speed comparison
- [wyoming-faster-whisper GitHub](https://github.com/rhasspy/wyoming-faster-whisper) -- Wyoming STT server

### TTS
- [Kokoro-82M HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M) -- Model card, 82M params, Apache license
- [Kokoro GitHub](https://github.com/hexgrad/kokoro) -- 8 languages, 54 voices, streaming
- [Piper GitHub (OHF-Voice)](https://github.com/OHF-Voice/piper1-gpl) -- Successor repo
- [wyoming-piper GitHub](https://github.com/rhasspy/wyoming-piper) -- Wyoming TTS server
- [Coqui TTS GitHub](https://github.com/coqui-ai/TTS) -- XTTS v2, voice cloning, archived project
- [Fish Speech GitHub](https://github.com/fishaudio/fish-speech) -- S1 model, 4B/0.5B params
- [F5-TTS GitHub](https://github.com/SWivid/F5-TTS) -- Diffusion transformer TTS
- [Bark GitHub](https://github.com/suno-ai/bark) -- Generative text-to-audio, 12 GB VRAM
- [CSM Sesame GitHub](https://github.com/SesameAILabs/csm) -- Conversational speech model
- [openedai-speech GitHub](https://github.com/matatonic/openedai-speech) -- OpenAI-compatible TTS server

### Wake Word
- [openWakeWord GitHub](https://github.com/dscripka/openWakeWord) -- ONNX wake word, custom training
- [Porcupine GitHub](https://github.com/Picovoice/porcupine) -- DNN wake word, Apache 2.0
- [wyoming-openwakeword GitHub](https://github.com/rhasspy/wyoming-openwakeword) -- Wyoming wake word server

### Architecture
- [Wyoming protocol GitHub](https://github.com/rhasspy/wyoming) -- Protocol specification
- [Speaches GitHub](https://github.com/speaches-ai/speaches) -- Unified STT+TTS server, OpenAI API
- [HA Wyoming integration](https://www.home-assistant.io/integrations/wyoming/) -- Configuration docs
- [HA Voice Control docs](https://www.home-assistant.io/voice_control/) -- Voice pipeline overview
- [$13 voice remote tutorial](https://www.home-assistant.io/voice_control/thirteen-usd-voice-remote/) -- M5Stack ATOM Echo setup
