from lib.transcripts.adapters.base import TranscriptAdapter


class AgyAdapter(TranscriptAdapter):
    def extract_usage(self, entry: dict) -> dict | None:
        # Agy adapter dummy
        return None
