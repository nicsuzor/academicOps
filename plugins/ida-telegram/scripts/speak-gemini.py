#!/usr/bin/env python3
"""
Synthesise speech using Gemini 3.8 Flash TTS and encode to Telegram OGG/Opus.

Usage:
    speak-gemini.py <text-file> <out.ogg>

Environment variables:
    GEMINI_API_KEY (or GOOGLE_API_KEY): Required Gemini API key.
    GEMINI_API_BASE_URL: Optional API base URL override (default: https://generativelanguage.googleapis.com).
    GEMINI_TTS_VOICE: Optional voice name (default: Aoede).
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 3:
        sys.stderr.write("Error: text file argument and output ogg argument required\n")
        sys.exit(1)

    text_file_path = Path(sys.argv[1]).expanduser()
    out_ogg_path = Path(sys.argv[2]).expanduser()

    if not text_file_path.exists() or not text_file_path.is_file():
        sys.stderr.write(f"Error: text file not found: {text_file_path}\n")
        sys.exit(1)

    try:
        text = text_file_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        sys.stderr.write(f"Error: failed to read text file: {e}\n")
        sys.exit(1)

    if not text:
        sys.stderr.write("Error: input text file is empty\n")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.stderr.write("Error: GEMINI_API_KEY environment variable is missing\n")
        sys.exit(1)

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        sys.stderr.write(
            "Error: ffmpeg is required to encode audio to OGG/Opus but is not found in PATH\n"
        )
        sys.exit(1)

    voice_name = os.environ.get("GEMINI_TTS_VOICE", "Aoede")
    base_url = os.environ.get(
        "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com"
    ).rstrip("/")
    endpoint = f"{base_url}/v1beta/models/gemini-3.8-flash-tts:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}},
        },
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=req_data, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_bytes = resp.read()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"Error: Gemini TTS API failure ({e.code}): {err_body}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: Gemini TTS network failure: {e}\n")
        sys.exit(1)

    try:
        resp_json = json.loads(resp_bytes.decode("utf-8"))
    except Exception as e:
        sys.stderr.write(f"Error: failed to parse Gemini TTS response JSON: {e}\n")
        sys.exit(1)

    candidates = resp_json.get("candidates", [])
    if not candidates:
        sys.stderr.write(f"Error: Gemini TTS returned no candidates: {resp_json}\n")
        sys.exit(1)

    audio_b64 = None
    mime_type = "audio/wav"
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline_data = part.get("inlineData")
        if inline_data and "data" in inline_data:
            audio_b64 = inline_data["data"]
            mime_type = inline_data.get("mimeType", mime_type)
            break

    if not audio_b64:
        sys.stderr.write(f"Error: Gemini TTS returned no audio data: {resp_json}\n")
        sys.exit(1)

    try:
        raw_audio = base64.b64decode(audio_b64)
    except Exception as e:
        sys.stderr.write(f"Error: failed to decode audio base64 data: {e}\n")
        sys.exit(1)

    out_ogg_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp_audio:
        tmp_audio_path = Path(tmp_audio.name)
        try:
            tmp_audio.write(raw_audio)
            tmp_audio.flush()
            tmp_audio.close()

            # Encode to OGG/Opus using ffmpeg
            # Telegram voice notes require Ogg container with Opus codec
            res = subprocess.run(
                [
                    ffmpeg_bin,
                    "-y",
                    "-i",
                    str(tmp_audio_path),
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "32k",
                    str(out_ogg_path),
                ],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                sys.stderr.write(
                    f"Error: ffmpeg failed to convert audio to OGG/Opus: {res.stderr}\n"
                )
                sys.exit(1)
        finally:
            if tmp_audio_path.exists():
                try:
                    tmp_audio_path.unlink()
                except OSError:
                    pass

    if not out_ogg_path.exists() or out_ogg_path.stat().st_size == 0:
        sys.stderr.write(f"Error: output audio file {out_ogg_path} was not created or is empty\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
