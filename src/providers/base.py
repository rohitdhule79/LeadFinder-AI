from typing import Protocol, Iterable

class ProviderError(Exception):
    pass

class SearchProvider(Protocol):
    name: str
    def search(self, criteria) -> Iterable[dict]: ...
