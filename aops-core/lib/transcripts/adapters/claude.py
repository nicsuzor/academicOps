from lib.transcripts.adapters.base import TranscriptAdapter


class ClaudeAdapter(TranscriptAdapter):
    def extract_usage(self, entry: dict) -> dict | None:
        if entry.get("type") != "assistant":
            return None
        if entry.get("isApiErrorMessage") or "error" in entry:
            return None

        msg = entry.get("message")
        if not msg:  # allow-fallback: msg may be null
            return None

        if msg.get("model") == "<synthetic>":
            return None

        usage = msg.get("usage")
        if not usage:  # allow-fallback: usage may be null
            return None

        return usage
