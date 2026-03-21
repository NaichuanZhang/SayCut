"use client";

import { useCallback, useRef, useState } from "react";

interface AudioRecorderResult {
  startRecording: () => Promise<void>;
  stopRecording: () => string | null;
  isRecording: boolean;
  analyserNode: AnalyserNode | null;
  error: string | null;
}

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const numSamples = samples.length;
  const bytesPerSample = 2;
  const blockAlign = bytesPerSample;
  const dataSize = numSamples * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, "WAVE");

  // fmt subchunk
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true); // bits per sample

  // data subchunk
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  // Write PCM samples
  let offset = 44;
  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return buffer;
}

function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

const SAMPLE_RATE = 16_000;
const BUFFER_SIZE = 4096;

export function useAudioRecorder(): AudioRecorderResult {
  const [isRecording, setIsRecording] = useState(false);
  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const samplesRef = useRef<Float32Array[]>([]);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      samplesRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      sourceRef.current = source;

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);

      // Capture PCM samples via ScriptProcessorNode
      const processor = ctx.createScriptProcessor(BUFFER_SIZE, 1, 1);
      processorRef.current = processor;
      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        samplesRef.current.push(new Float32Array(input));
      };
      source.connect(processor);
      processor.connect(ctx.destination);

      setAnalyserNode(analyser);
      setIsRecording(true);
      console.debug("[SayCut] Recording started, sampleRate:", SAMPLE_RATE);
    } catch (err) {
      const message =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone permission denied. Please allow mic access to use voice."
          : "Failed to start recording.";
      console.debug("[SayCut] Recording error:", message);
      setError(message);
    }
  }, []);

  const stopRecording = useCallback((): string | null => {
    // Collect samples before cleanup
    const chunks = samplesRef.current;
    samplesRef.current = [];

    processorRef.current?.disconnect();
    processorRef.current = null;

    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;

    sourceRef.current?.disconnect();
    sourceRef.current = null;

    if (audioContextRef.current?.state !== "closed") {
      audioContextRef.current?.close();
    }
    audioContextRef.current = null;

    setAnalyserNode(null);
    setIsRecording(false);

    if (chunks.length === 0) {
      console.debug("[SayCut] Recording stopped: no samples captured");
      return null;
    }

    // Merge all chunks into a single Float32Array
    const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Encode to WAV and return as base64
    const wavBuffer = encodeWav(merged, SAMPLE_RATE);
    console.debug(
      "[SayCut] Recording stopped: samples=%d, WAV size=%d bytes",
      totalLength,
      wavBuffer.byteLength,
    );
    return arrayBufferToBase64(wavBuffer);
  }, []);

  return { startRecording, stopRecording, isRecording, analyserNode, error };
}
