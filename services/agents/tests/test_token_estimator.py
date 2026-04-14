"""Tests for the tiktoken-based token estimator."""

from __future__ import annotations

from unittest.mock import patch

from m2la_agents.token_estimator import estimate_message_tokens, estimate_text_tokens


class TestEstimateTextTokens:
    """Tests for estimate_text_tokens()."""

    def test_empty_string_returns_zero(self) -> None:
        assert estimate_text_tokens("") == 0

    def test_none_like_empty_returns_zero(self) -> None:
        # Empty strings are falsy — should short-circuit.
        assert estimate_text_tokens("") == 0

    def test_simple_text_returns_positive(self) -> None:
        result = estimate_text_tokens("Hello, world!")
        assert result > 0

    def test_longer_text_returns_more_tokens(self) -> None:
        short = estimate_text_tokens("Hello")
        long = estimate_text_tokens("Hello, this is a much longer sentence with many words in it.")
        assert long > short

    def test_tiktoken_unavailable_returns_zero(self) -> None:
        with patch("m2la_agents.token_estimator._get_encoding", side_effect=Exception("unavailable")):
            result = estimate_text_tokens("some text")
        assert result == 0


class TestEstimateMessageTokens:
    """Tests for estimate_message_tokens()."""

    def test_empty_list_returns_zero(self) -> None:
        assert estimate_message_tokens([]) == 0

    def test_single_message_returns_positive(self) -> None:
        messages = [{"role": "user", "content": "Hello"}]
        result = estimate_message_tokens(messages)
        # Must be > 0 and include per-message + reply-primer overhead.
        assert result > 0

    def test_message_with_name_adds_overhead(self) -> None:
        without_name = [{"role": "user", "content": "Hello"}]
        with_name = [{"role": "user", "content": "Hello", "name": "alice"}]
        result_without = estimate_message_tokens(without_name)
        result_with = estimate_message_tokens(with_name)
        # 'name' key adds _TOKENS_PER_NAME (1) plus tokens for the name value.
        assert result_with > result_without

    def test_multiple_messages_adds_overhead_per_message(self) -> None:
        single = [{"role": "user", "content": "Hi"}]
        double = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        result_single = estimate_message_tokens(single)
        result_double = estimate_message_tokens(double)
        assert result_double > result_single

    def test_tiktoken_unavailable_returns_zero(self) -> None:
        with patch("m2la_agents.token_estimator._get_encoding", side_effect=Exception("unavailable")):
            result = estimate_message_tokens([{"role": "user", "content": "Hello"}])
        assert result == 0
