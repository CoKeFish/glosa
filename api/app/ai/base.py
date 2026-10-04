"""The only AI interface the rest of the app sees.

Features ask for a model by capability ("text") and call `complete`. Which
provider and model answer is configuration, stored in settings, so switching
from Claude to a local model never touches feature code.
"""

from dataclasses import dataclass
from typing import Protocol


class AIError(Exception):
    pass


class AINotConfigured(AIError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    base_url: str | None = None


class TextModel(Protocol):
    async def complete(self, system: str, prompt: str, max_tokens: int = 4000) -> str: ...
