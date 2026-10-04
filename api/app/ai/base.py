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


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0  # includes thinking tokens where the provider bills them


class TextModel(Protocol):
    model: str
    # Tokens of the last completed call, as reported by the provider (for cost estimates).
    last_usage: Usage | None

    async def complete(self, system: str, prompt: str, max_tokens: int = 4000) -> str: ...
