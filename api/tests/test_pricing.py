from app.ai.pricing import cost, price


def test_known_and_dated_anthropic_prices():
    assert price("anthropic", "claude-opus-5-5", {}) == (4.0, 20.0)
    assert price("anthropic", "claude-haiku-4-5-20251001", {}) == (1.0, 5.0)
    assert price("anthropic", "claude-opus-5", {}) == (5.0, 25.0)  # not confused with opus-5-5


def test_unknown_local_and_custom_prices():
    assert price("openai", "gpt-5.5", {}) is None
    assert price("openai", "gpt-5.5", {"gpt-5.5": {"input": 2.5, "output": 10}}) == (2.5, 10.0)
    assert price("openai_compatible", "gemma3:4b", {}) == (0.0, 0.0)


def test_deepseek_prices():
    assert price("deepseek", "deepseek-v4-pro", {}) == (1.74, 3.48)
    assert price("deepseek", "deepseek-flash", {}) is None  # newer than the documented table


def test_cost():
    assert cost(1_000_000, 0, (4.0, 20.0)) == 4.0
    assert round(cost(229, 120, (4.0, 20.0)), 6) == 0.003316
    assert cost(100, 100, None) is None
