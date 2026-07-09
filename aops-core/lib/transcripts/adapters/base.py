from abc import ABC, abstractmethod


class TranscriptAdapter(ABC):
    @abstractmethod
    def extract_usage(self, entry: dict) -> dict | None:
        pass
