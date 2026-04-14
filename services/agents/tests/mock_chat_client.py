"""MockChatClient — test infrastructure for simulating LLM tool-calling.

This module provides :class:`MockChatClient`, a lightweight implementation of
the ``SupportsChatGetResponse`` protocol from the Microsoft Agent Framework.

When used as the ``client`` parameter to ``Agent(client=..., ...)``, it
simulates the LLM's tool-calling behaviour:

1. On the **first** call, it inspects the tool definitions passed via
   ``options`` and emits a ``function_call`` content item for the first
   available tool.  The ``FunctionInvocationLayer`` middleware inside
   ``Agent`` then invokes the actual Python function.
2. On the **second** call (after the function result has been appended to
   the conversation), it returns a text summary of the tool result.

This is **test-only** infrastructure.  It is not a product feature, not an
"offline mode", and must not appear in production code paths.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, Mapping, Sequence
from typing import Any

from agent_framework import ChatResponse, ChatResponseUpdate, Content, Message
from agent_framework._types import ResponseStream


class MockChatClient:
    """Simulates LLM tool-calling for tests.

    Implements the ``SupportsChatGetResponse`` protocol via duck typing.
    The Agent's ``FunctionInvocationLayer`` handles the actual tool
    invocation after receiving the ``function_call`` content we return.
    """

    additional_properties: dict[str, Any]

    def __init__(self) -> None:
        self.additional_properties = {}
        self.call_count = 0

    # ------------------------------------------------------------------
    # SupportsChatGetResponse protocol
    # ------------------------------------------------------------------

    def get_response(
        self,
        messages: Sequence[Message],
        *,
        stream: bool = False,
        options: Any | None = None,
        compaction_strategy: Any | None = None,
        tokenizer: Any | None = None,
        function_invocation_kwargs: Mapping[str, Any] | None = None,
        client_kwargs: Mapping[str, Any] | None = None,
    ) -> Any:
        """Return an awaitable ``ChatResponse`` or a ``ResponseStream``.

        On the first invocation (no function results in messages yet),
        returns a ``function_call`` for the first available tool so the
        Agent middleware invokes the real tool function.

        On subsequent invocations (function results present), returns a
        plain text summary.
        """
        self.call_count += 1

        # Check if there are already function results in the conversation
        has_function_result = any(
            any(c.type == "function_result" for c in msg.contents) for msg in messages if msg.contents
        )

        # Extract tool definitions from options (if available)
        tool_defs = self._extract_tool_defs(options)

        if not has_function_result and tool_defs:
            # First call: request a tool invocation
            response = self._make_function_call_response(messages, tool_defs)
        else:
            # Second call (or no tools): return text summary
            response = self._make_text_response(messages)

        if stream:
            return self._as_stream(response)
        return self._as_awaitable(response)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_tool_defs(options: Any | None) -> list[dict[str, Any]]:
        """Pull tool schemas from the options dict passed by Agent."""
        if options is None:
            return []
        tools: list[dict[str, Any]] = []
        raw_tools = None
        if isinstance(options, dict):
            raw_tools = options.get("tools")
        elif hasattr(options, "get"):
            raw_tools = options.get("tools")  # type: ignore[union-attr]
        if raw_tools is None:
            return []
        for t in raw_tools:
            if isinstance(t, dict):
                tools.append(t)
            elif hasattr(t, "model_dump"):
                tools.append(t.model_dump())
            else:
                tools.append({"type": "function", "function": {"name": str(t)}})
        return tools

    @staticmethod
    def _make_function_call_response(
        messages: Sequence[Message],
        tool_defs: list[dict[str, Any]],
    ) -> ChatResponse[Any]:
        """Build a ``ChatResponse`` that requests invocation of the first tool."""
        # Pick the first function tool
        func_name = ""
        func_params: dict[str, Any] = {}

        for td in tool_defs:
            fn = td.get("function") or td
            name = fn.get("name", "")
            if name:
                func_name = name
                # Try to build minimal arguments from the schema
                func_params = MockChatClient._infer_arguments(
                    fn.get("parameters", {}),
                    messages,
                )
                break

        if not func_name:
            # Fallback to text if no tools found
            return MockChatClient._make_text_response(messages)

        call_content = Content.from_function_call(
            call_id=f"mock-call-{func_name}",
            name=func_name,
            arguments=json.dumps(func_params),
        )

        response_msg = Message(
            role="assistant",
            contents=[call_content],
        )

        return ChatResponse(
            messages=[response_msg],
            response_id="mock-response-fc",
            finish_reason="tool_calls",
        )

    @staticmethod
    def _make_text_response(messages: Sequence[Message]) -> ChatResponse[Any]:
        """Build a plain text ``ChatResponse`` summarising tool results."""
        # Collect any function results from conversation
        summaries: list[str] = []
        for msg in messages:
            if not msg.contents:
                continue
            for content in msg.contents:
                if content.type == "function_result":
                    result_data = content.result if hasattr(content, "result") else ""
                    summaries.append(str(result_data))

        if summaries:
            text = f"Tool execution completed. Results: {'; '.join(summaries)}"
        else:
            # No function results — just echo the last user message
            last_user = ""
            for msg in reversed(list(messages)):
                if msg.role == "user" and msg.text:
                    last_user = msg.text
                    break
            text = f"Acknowledged: {last_user}" if last_user else "Mock response — no tools available."

        response_msg = Message(role="assistant", contents=[text])

        return ChatResponse(
            messages=[response_msg],
            response_id="mock-response-text",
            finish_reason="stop",
        )

    @staticmethod
    def _infer_arguments(
        param_schema: dict[str, Any],
        messages: Sequence[Message],
    ) -> dict[str, Any]:
        """Build minimal arguments for a tool call from the message context.

        Extracts ``input_path``, ``mode``, ``ir_json``, etc. from the
        user message so the deterministic tool functions receive real
        data to work with.
        """
        user_text = ""
        for msg in reversed(list(messages)):
            if msg.role == "user" and msg.text:
                user_text = msg.text
                break

        # Parse the user message for common parameters
        args: dict[str, Any] = {}
        props = param_schema.get("properties", {})

        for prop_name in props:
            if prop_name == "input_path":
                # Extract path from user message
                for line in user_text.split("\n"):
                    if "project at:" in line.lower() or "path" in line.lower():
                        path = line.split(":", 1)[-1].strip()
                        if path:
                            args["input_path"] = path
                            break
            elif prop_name == "mode":
                for line in user_text.split("\n"):
                    if "input mode:" in line.lower():
                        mode = line.split(":", 1)[-1].strip()
                        if mode != "auto-detect":
                            args["mode"] = mode
                        break
            elif prop_name == "ir_json":
                # Look for IR data in function results from prior messages
                for msg in messages:
                    if not msg.contents:
                        continue
                    for content in msg.contents:
                        if content.type == "function_result" and hasattr(content, "result"):
                            args["ir_json"] = str(content.result)
                            break
                    if "ir_json" in args:
                        break
            elif prop_name == "output_directory":
                for line in user_text.split("\n"):
                    if "output directory:" in line.lower():
                        val = line.split(":", 1)[-1].strip()
                        if val != "default":
                            args["output_directory"] = val
                        break

        return args

    @staticmethod
    def _as_awaitable(response: ChatResponse[Any]) -> Any:
        """Wrap a ``ChatResponse`` in a coroutine."""

        async def _coro() -> ChatResponse[Any]:
            return response

        return _coro()

    @staticmethod
    def _as_stream(response: ChatResponse[Any]) -> ResponseStream[ChatResponseUpdate, ChatResponse[Any]]:
        """Wrap a ``ChatResponse`` as a ``ResponseStream``."""
        text = ""
        if response.messages:
            msg = response.messages[0] if isinstance(response.messages, list) else response.messages
            if hasattr(msg, "text"):
                text = msg.text or ""

        async def _stream() -> AsyncIterable[ChatResponseUpdate]:
            yield ChatResponseUpdate(
                role="assistant",
                contents=[Content.from_text(text)] if text else None,
                response_id=response.response_id,
                finish_reason="stop",
            )

        return ResponseStream(
            _stream(),
            finalizer=lambda _updates: response,
        )
