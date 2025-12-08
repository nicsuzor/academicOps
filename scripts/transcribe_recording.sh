#!/bin/bash
#
# Records audio in chunks using SoX, transcribing each chunk as it completes.
# Transcripts are appended to a single markdown file with bmem-compliant frontmatter.

# --- Configuration ---
RECORDINGS_DIR="$HOME/src/recordings"
TRANSCRIPTS_DIR="${ACA_DATA}/transcripts"
CHUNK_MINUTES=2  # Duration of each chunk in minutes

# --- Pre-flight Checks ---
if ! command -v sox &> /dev/null; then
    echo "ERROR: sox is not installed. Please install it to continue."
    echo "On macOS: brew install sox"
    exit 1
fi
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud is not installed. Please install and configure it to continue."
    exit 1
fi
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is not installed. Please install it to parse the API response."
    echo "On macOS: brew install jq"
    exit 1
fi

# Ensure directories exist
mkdir -p "$RECORDINGS_DIR" "$TRANSCRIPTS_DIR"

# --- Script Start ---
SESSION_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATETIME_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TRANSCRIPT_FILE="${TRANSCRIPTS_DIR}/${SESSION_TIMESTAMP}.md"
SESSION_DIR="${RECORDINGS_DIR}/session_${SESSION_TIMESTAMP}"
mkdir -p "$SESSION_DIR"

echo "=== Chunked Recording Session ==="
echo "Chunk duration: ${CHUNK_MINUTES} minutes"
echo "Audio chunks:   ${SESSION_DIR}/"
echo "Transcript:     ${TRANSCRIPT_FILE}"
echo ""
echo "Press Ctrl+C to stop the session."
echo ""

# Write initial frontmatter
cat << EOF > "$TRANSCRIPT_FILE"
---
title: "Audio Transcript - ${SESSION_TIMESTAMP}"
date: ${DATETIME_ISO}
source_audio: "${SESSION_DIR}"
tags:
  - transcript
  - automated
compliance:
  tool: "transcribe_recording.sh"
  api: "google-speech-to-text"
---

EOF

# Trap Ctrl+C to exit gracefully
KEEP_RECORDING=true
trap 'KEEP_RECORDING=false; echo ""; echo "Stopping after current chunk...";' INT

CHUNK_NUM=0

# Function to transcribe a chunk in background
transcribe_chunk() {
    local audio_file="$1"
    local chunk_id="$2"

    echo "[Chunk $chunk_id] Transcribing..."

    TRANSCRIPT_JSON=$(gcloud ml speech recognize "$audio_file" --language-code=en-US 2>&1)

    if [[ "$TRANSCRIPT_JSON" == "{"* ]]; then
        TRANSCRIPT_TEXT=$(echo "$TRANSCRIPT_JSON" | jq -r '.results | map(.alternatives[0].transcript) | join(" ")')
        if [ -n "$TRANSCRIPT_TEXT" ] && [ "$TRANSCRIPT_TEXT" != "null" ]; then
            echo "" >> "$TRANSCRIPT_FILE"
            echo "$TRANSCRIPT_TEXT" >> "$TRANSCRIPT_FILE"
            echo "[Chunk $chunk_id] ✓ Transcribed"
        else
            echo "[Chunk $chunk_id] (no speech detected)"
        fi
    else
        echo "[Chunk $chunk_id] ✗ Transcription failed"
    fi
}

# Main recording loop
while $KEEP_RECORDING; do
    CHUNK_NUM=$((CHUNK_NUM + 1))
    CHUNK_FILE="${SESSION_DIR}/chunk_$(printf '%03d' $CHUNK_NUM).wav"

    echo "[Chunk $CHUNK_NUM] Recording for ${CHUNK_MINUTES} minutes..."

    # Record for CHUNK_MINUTES (sox uses seconds)
    CHUNK_SECONDS=$((CHUNK_MINUTES * 60))
    rec --clobber "$CHUNK_FILE" trim 0 $CHUNK_SECONDS 2>/dev/null
    REC_EXIT=$?

    # Check if we got a valid file
    if [ -f "$CHUNK_FILE" ] && [ -s "$CHUNK_FILE" ]; then
        echo "[Chunk $CHUNK_NUM] Saved: $CHUNK_FILE"
        # Transcribe in background so next chunk can start
        transcribe_chunk "$CHUNK_FILE" "$CHUNK_NUM" &
    else
        echo "[Chunk $CHUNK_NUM] No audio captured"
    fi

    # If rec was interrupted (Ctrl+C), the trap sets KEEP_RECORDING=false
done

# Wait for any remaining transcription jobs
echo ""
echo "Waiting for transcriptions to complete..."
wait

echo ""
echo "=== Session Complete ==="
echo "Audio chunks: ${SESSION_DIR}/"
echo "Transcript:   ${TRANSCRIPT_FILE}"
