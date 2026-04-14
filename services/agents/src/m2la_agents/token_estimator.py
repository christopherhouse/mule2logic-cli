"""Token estimation utilities using tiktoken.

Provides pre-call prompt token estimation and post-call completion token
estimation using the ``cl100k_base`` encoding (GPT-4o / GPT-4 / GPT-3.5-turbo
family).

The encoding instance is cached for performance.
"""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# Default encoding for GPT-4o family models.
_DEFAULT_ENCODING_NAME = "cl100k_base"

# Overhead tokens per message in chat format.
# Every message follows <|start|>{role/name}\n{content}<|end|>\n
_TOKENS_PER_MESSAGE = 3
_TOKENS_PER_NAME = 1
# Every reply is primed with <|start|>assistant<|message|>
_REPLY_PRIMER_TOKENS = 3


@lru_cache(maxsize=1)
def _get_encoding(encoding_name: str = _DEFAULT_ENCODING_NAME):  # type: ignore[no-untyped-def]
    """Return a cached tiktoken encoding instance."""
    import tiktoken

    return tiktoken.get_encoding(encoding_name)


def estimate_text_tokens(text: str, *, encoding_name: str = _DEFAULT_ENCODING_NAME) -> int:
    """Estimate the number of tokens for a plain text string.

    Args:
        text: The text to tokenize.
        encoding_name: The tiktoken encoding to use.

    Returns:
        Estimated token count. Returns 0 if tiktoken is unavailable.
    """
    if not text:
        return 0
    try:
        enc = _get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        logger.debug("tiktoken unavailable — returning 0 for text token estimate")
        return 0


def estimate_message_tokens(
    messages: list[dict[str, str]],
    *,
    encoding_name: str = _DEFAULT_ENCODING_NAME,
) -> int:
    """Estimate prompt tokens for a chat-format message list.

    Uses the OpenAI token counting recipe with per-message and per-name
    overhead.

    Args:
        messages: List of chat messages, each with ``role`` and ``content``
            keys.  Optionally ``name``.
        encoding_name: The tiktoken encoding to use.

    Returns:
        Estimated prompt token count. Returns 0 if tiktoken is unavailable.
    """
    if not messages:
        return 0
    try:
        enc = _get_encoding(encoding_name)
    except Exception:
        logger.debug("tiktoken unavailable — returning 0 for message token estimate")
        return 0

    num_tokens = 0
    for message in messages:
        num_tokens += _TOKENS_PER_MESSAGE
        for key, value in message.items():
            num_tokens += len(enc.encode(str(value)))
            if key == "name":
                num_tokens += _TOKENS_PER_NAME
    # Every reply is primed with <|start|>assistant<|message|>
    num_tokens += _REPLY_PRIMER_TOKENS
    return num_tokens
