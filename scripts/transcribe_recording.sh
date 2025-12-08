#!/bin/bash
#
# Records audio in chunks using SoX, transcribing via Google Cloud Speech-to-Text async API.
# Transcripts are appended to a single markdown file with bmem-compliant frontmatter.
#
# Usage:
#   transcribe_recording.sh [session_name]     # Start new recording session
#   transcribe_recording.sh --resume [dir]     # Resume/transcribe existing session

set -euo pipefail

# --- Configuration ---
RECORDINGS_DIR="$HOME/src/recordings"
TRANSCRIPTS_DIR="${ACA_DATA}/transcripts"
GCS_BUCKET="gs://prosocial-dev/tmp/transcribe"
CHUNK_MINUTES=2

# --- Pre-flight Checks ---
for cmd in sox gcloud jq; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "ERROR: $cmd is not installed." >&2
        exit 1
    fi
done

mkdir -p "$RECORDINGS_DIR" "$TRANSCRIPTS_DIR"

# --- Helper Functions ---

upload_and_transcribe() {
    local wav_file="$1"
    local session_dir="$2"
    local tracking_file="${session_dir}/operations.json"

    local basename=$(basename "$wav_file" .wav)
    local flac_file="${wav_file%.wav}.flac"
    local gcs_path="${GCS_BUCKET}/$(basename "$session_dir")/${basename}.flac"

    # Convert to FLAC (16-bit, mono, 16kHz - optimal for speech recognition)
    sox "$wav_file" -r 16000 -c 1 -b 16 "$flac_file" 2>/dev/null

    # Upload to GCS
    gsutil -q cp "$flac_file" "$gcs_path"
    rm -f "$flac_file"

    # Start async recognition (latest_long = Chirp model for long-form audio)
    local result=$(gcloud ml speech recognize-long-running "$gcs_path" \
        --language-code=en-US \
        --model=latest_long \
        --async \
        --format=json 2>&1)

    local op_name=$(echo "$result" | jq -r '.name // empty')
    if [ -n "$op_name" ]; then
        # Track operation
        local entry=$(jq -n --arg wav "$wav_file" --arg op "$op_name" --arg gcs "$gcs_path" \
            '{wav: $wav, operation: $op, gcs: $gcs, status: "pending"}')

        if [ -f "$tracking_file" ]; then
            jq --argjson new "$entry" '. += [$new]' "$tracking_file" > "${tracking_file}.tmp"
            mv "${tracking_file}.tmp" "$tracking_file"
        else
            echo "[$entry]" > "$tracking_file"
        fi
        echo "[$(basename "$wav_file")] Started transcription: $op_name"
    else
        echo "[$(basename "$wav_file")] ERROR: Failed to start transcription" >&2
        echo "$result" >&2
    fi
}

collect_transcripts() {
    local session_dir="$1"
    local transcript_file="$2"
    local tracking_file="${session_dir}/operations.json"

    if [ ! -f "$tracking_file" ]; then
        echo "No pending operations found."
        return
    fi

    local pending=$(jq '[.[] | select(.status == "pending")]' "$tracking_file")
    local count=$(echo "$pending" | jq 'length')

    if [ "$count" -eq 0 ]; then
        echo "All transcriptions already complete."
        return
    fi

    echo "Waiting for $count transcription(s)..."

    # Process each pending operation (avoid subshell with process substitution)
    while IFS= read -r entry; do
        local op=$(echo "$entry" | jq -r '.operation')
        local wav=$(echo "$entry" | jq -r '.wav')
        local gcs=$(echo "$entry" | jq -r '.gcs')

        echo "[$(basename "$wav")] Waiting for operation..."
        local result=$(gcloud ml speech operations wait "$op" --format=json 2>/dev/null)

        if echo "$result" | jq -e '.results' > /dev/null 2>&1; then
            local text=$(echo "$result" | jq -r '.results | map(.alternatives[0].transcript) | join(" ")')
            if [ -n "$text" ] && [ "$text" != "null" ]; then
                echo "" >> "$transcript_file"
                echo "$text" >> "$transcript_file"
                echo "[$(basename "$wav")] ✓ Transcribed"
            else
                echo "[$(basename "$wav")] (no speech detected)"
            fi
        else
            echo "[$(basename "$wav")] ✗ Transcription failed" >&2
            echo "$result" | head -5 >&2
        fi

        # Delete from GCS
        gsutil -q rm "$gcs" 2>/dev/null || true

        # Mark as complete
        jq --arg op "$op" '(.[] | select(.operation == $op)).status = "complete"' "$tracking_file" > "${tracking_file}.tmp"
        mv "${tracking_file}.tmp" "$tracking_file"
    done < <(echo "$pending" | jq -c '.[]')
}

# --- Main Logic ---

if [ "${1:-}" = "--resume" ]; then
    # Resume mode: transcribe existing session
    SESSION_DIR="${2:-$(ls -td "$RECORDINGS_DIR"/session_* 2>/dev/null | head -1)}"

    if [ -z "$SESSION_DIR" ] || [ ! -d "$SESSION_DIR" ]; then
        echo "ERROR: No session directory found" >&2
        exit 1
    fi

    SESSION_NAME=$(basename "$SESSION_DIR" | sed 's/session_//')
    TRANSCRIPT_FILE="${TRANSCRIPTS_DIR}/${SESSION_NAME}.md"

    echo "=== Resuming Session: $SESSION_NAME ==="
    echo "Session dir:  $SESSION_DIR"
    echo "Transcript:   $TRANSCRIPT_FILE"
    echo ""

    # Create transcript file if needed
    if [ ! -f "$TRANSCRIPT_FILE" ]; then
        DATETIME_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        cat << EOF > "$TRANSCRIPT_FILE"
---
title: "Audio Transcript - ${SESSION_NAME}"
date: ${DATETIME_ISO}
source_audio: "${SESSION_DIR}"
tags:
  - transcript
  - automated
---

EOF
    fi

    # Upload any WAV files not yet tracked
    TRACKING_FILE="${SESSION_DIR}/operations.json"
    for wav in "$SESSION_DIR"/chunk_*.wav; do
        [ -f "$wav" ] || continue
        if [ -f "$TRACKING_FILE" ] && jq -e --arg w "$wav" '.[] | select(.wav == $w)' "$TRACKING_FILE" > /dev/null 2>&1; then
            continue  # Already tracked
        fi
        upload_and_transcribe "$wav" "$SESSION_DIR"
    done

    # Collect results
    collect_transcripts "$SESSION_DIR" "$TRANSCRIPT_FILE"

    # Cleanup GCS folder
    gsutil -q rm -r "${GCS_BUCKET}/$(basename "$SESSION_DIR")" 2>/dev/null || true

    echo ""
    echo "=== Session Complete ==="
    echo "Transcript: $TRANSCRIPT_FILE"

else
    # Recording mode
    SESSION_NAME="${1:-$(date +%Y%m%d_%H%M%S)}"
    SESSION_DIR="${RECORDINGS_DIR}/session_${SESSION_NAME}"
    TRANSCRIPT_FILE="${TRANSCRIPTS_DIR}/${SESSION_NAME}.md"

    mkdir -p "$SESSION_DIR"

    echo "=== Recording Session: $SESSION_NAME ==="
    echo "Chunk duration: ${CHUNK_MINUTES} minutes"
    echo "Audio chunks:   ${SESSION_DIR}/"
    echo "Transcript:     ${TRANSCRIPT_FILE}"
    echo ""
    echo "Press Ctrl+C to stop recording."
    echo ""

    # Write initial frontmatter
    DATETIME_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cat << EOF > "$TRANSCRIPT_FILE"
---
title: "Audio Transcript - ${SESSION_NAME}"
date: ${DATETIME_ISO}
source_audio: "${SESSION_DIR}"
tags:
  - transcript
  - automated
---

EOF

    KEEP_RECORDING=true
    trap 'KEEP_RECORDING=false; echo ""; echo "Stopping after current chunk...";' INT

    CHUNK_NUM=0
    CHUNK_SECONDS=$((CHUNK_MINUTES * 60))

    while $KEEP_RECORDING; do
        CHUNK_NUM=$((CHUNK_NUM + 1))
        CHUNK_FILE="${SESSION_DIR}/chunk_$(printf '%03d' $CHUNK_NUM).wav"

        echo "[Chunk $CHUNK_NUM] Recording for ${CHUNK_MINUTES} minutes..."

        rec --clobber "$CHUNK_FILE" trim 0 $CHUNK_SECONDS 2>/dev/null || true

        if [ -f "$CHUNK_FILE" ] && [ -s "$CHUNK_FILE" ]; then
            echo "[Chunk $CHUNK_NUM] Saved: $CHUNK_FILE"
            upload_and_transcribe "$CHUNK_FILE" "$SESSION_DIR" &
        else
            echo "[Chunk $CHUNK_NUM] No audio captured"
        fi
    done

    echo ""
    echo "Recording stopped. Collecting transcripts..."
    wait

    collect_transcripts "$SESSION_DIR" "$TRANSCRIPT_FILE"

    # Cleanup GCS folder
    gsutil -q rm -r "${GCS_BUCKET}/$(basename "$SESSION_DIR")" 2>/dev/null || true

    echo ""
    echo "=== Session Complete ==="
    echo "Audio chunks: ${SESSION_DIR}/"
    echo "Transcript:   ${TRANSCRIPT_FILE}"
fi
