# Audio Generation Pipeline

*Emerging capability. The field is evolving fast. No specific model choices locked.*

---

## Use Cases for Athanor

1. **EoBQ Ambiance:** Background music and sound effects for game scenes — procedurally generated to match scene mood
2. **EoBQ Voice Acting:** Text-to-speech for character dialogue using voice cloning or style-specific TTS — each character has a distinct voice
3. **Voice Interface for Athanor:** Speech-to-text (Whisper-class) → agent processing → text-to-speech response. Enables voice interaction with the system.
4. **Music Generation:** Personal creative tool — generate music based on mood, style, reference tracks
5. **Content Production:** Audio post-processing (noise removal, enhancement, mastering)

---

## Model Landscape (Feb 2026)

| Category | Models | Notes |
|----------|--------|-------|
| Text-to-Speech | Bark (Suno), XTTS-v2 (Coqui), StyleTTS2, OpenVoice, F5-TTS | All run locally, varying quality |
| Music Generation | MusicGen (Meta), Stable Audio, AudioCraft | MusicGen runs locally on GPU |
| Speech-to-Text | Whisper variants (OpenAI), Whisper.cpp (CPU), Distil-Whisper (speed) | Whisper is the standard |
| Sound Effects | AudioGen (Meta) | Text-to-sound-effect generation |
| Voice Cloning | RVC, So-VITS-SVC, OpenVoice | Clone voice from samples, generate speech in that voice |

---

## Infrastructure Integration

- Audio models are generally small (1-4 GB VRAM) compared to LLMs
- TTS can run on any 5070 Ti or the RTX 5060 Ti — doesn't need the 5090
- STT (Whisper) can run on CPU for non-real-time, GPU for real-time voice interface
- Audio generation integrates into ComfyUI via audio nodes, or standalone containers
- For EoBQ: the Creative Agent triggers audio generation as part of the scene rendering pipeline

---

## Deployment Pattern

Same as other creative tools:
- Docker containers on Node 2
- Models staged from Tier 2 (VAULT NVMe) to Tier 1 (node local NVMe)
- Called via API from the agent framework or directly from EoBQ's game engine
