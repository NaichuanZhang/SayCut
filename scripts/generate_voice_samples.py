"""One-off script to generate voice sample WAV files for the mode selector UI."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bosonUtil.eigen_tts import synthesize_speech

SAMPLE_TEXT = "Hello, how are you doing today?"
VOICES = ["Linda", "Jack"]
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "public",
    "voice-samples",
)


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for voice in VOICES:
        print(f"Generating sample for {voice}...")
        result = await synthesize_speech(SAMPLE_TEXT, voice=voice)
        output_path = os.path.join(OUTPUT_DIR, f"{voice.lower()}.wav")
        with open(output_path, "wb") as f:
            f.write(result.wav_bytes)
        print(f"  Saved: {output_path} ({result.duration_s:.1f}s)")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
