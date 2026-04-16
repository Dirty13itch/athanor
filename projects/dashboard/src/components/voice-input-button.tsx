"use client";

import { Mic, MicOff, Volume2 } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export function VoiceInputButton({ onTranscript, disabled }: VoiceInputButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });

        // Send to Whisper STT
        const formData = new FormData();
        formData.append("file", audioBlob, "recording.webm");
        formData.append("model", "whisper-large-v3");

        try {
          const res = await fetch("/api/stt", { method: "POST", body: formData });
          if (res.ok) {
            const data = await res.json();
            onTranscript(data.text || "");
          }
        } catch {
          // Fallback: try browser SpeechRecognition
          console.error("STT service unavailable");
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    } catch {
      console.error("Microphone access denied");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setIsRecording(false);
  }

  return (
    <Button
      size="icon"
      variant="ghost"
      disabled={disabled}
      onClick={isRecording ? stopRecording : startRecording}
      className={cn(
        "shrink-0",
        isRecording && "text-red-400 animate-pulse"
      )}
      title={isRecording ? "Stop recording" : "Voice input"}
    >
      {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
    </Button>
  );
}

interface TtsPlayButtonProps {
  text: string;
}

export function TtsPlayButton({ text }: TtsPlayButtonProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function play() {
    if (isPlaying) {
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }

    try {
      setIsPlaying(true);
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: text.slice(0, 2000), voice: "alloy" }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => {
          setIsPlaying(false);
          URL.revokeObjectURL(url);
        };
        audio.play();
      }
    } catch {
      setIsPlaying(false);
    }
  }

  if (!text || text.length < 10) return null;

  return (
    <button
      onClick={play}
      className={cn(
        "inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary transition-colors",
        isPlaying && "text-primary"
      )}
      title={isPlaying ? "Stop" : "Read aloud"}
    >
      <Volume2 className="h-3 w-3" />
      {isPlaying ? "Stop" : "Listen"}
    </button>
  );
}
