from typing import Protocol


class ProviderError(RuntimeError):
    def __init__(self, code, message, *, retry_after_seconds=None, quota_kind=None, retryable=None):
        super().__init__(message)
        self.code = code
        self.retry_after_seconds = retry_after_seconds
        self.quota_kind = quota_kind
        self.retryable = retryable


class Provider(Protocol):
    name: str
    simulated: bool

    def generate(self, system: str, prompt: str) -> dict: ...
