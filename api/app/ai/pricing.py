"""Model prices, to estimate what the AI features cost.

Anthropic list prices in USD per million tokens (input, output), as published in
September 2026. Output includes thinking tokens. Models not listed here have no known
price: the reader can enter one in the settings ("ai.prices"), and local servers are free.
"""

ANTHROPIC = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

# DeepSeek prices from its API docs (agent integration guide, 2026), cache-miss input.
# "deepseek-flash" (V4.1) is newer than that table and has no documented price here.
DEEPSEEK = {
    "deepseek-v4-pro": (1.74, 3.48),
    "deepseek-v4-flash": (0.14, 0.28),
}

# Typical tokens (input, output) per feature, used before there is any recorded usage.
TYPICAL_TOKENS = {
    "translate": (150, 150),
    "explain": (300, 300),
    "expressions": (400, 400),
    "grammar": (400, 500),
}


def price(provider: str, model: str, custom: dict[str, dict]) -> tuple[float, float] | None:
    """(input, output) USD per million tokens, or None when unknown."""
    if model in custom:
        p = custom[model]
        return float(p["input"]), float(p["output"])
    if provider == "openai_compatible":
        return (0.0, 0.0)  # a local server (Ollama, LM Studio); a paid gateway needs a custom price
    if provider == "deepseek":
        return DEEPSEEK.get(model)
    if provider == "anthropic":
        # Dated ids ("claude-haiku-4-5-20251001") share the alias's price.
        for name, p in sorted(ANTHROPIC.items(), key=lambda kv: -len(kv[0])):
            if model == name or model.startswith(name + "-"):
                return p
    return None


def cost(tokens_in: int, tokens_out: int, p: tuple[float, float] | None) -> float | None:
    if p is None:
        return None
    return (tokens_in * p[0] + tokens_out * p[1]) / 1_000_000
