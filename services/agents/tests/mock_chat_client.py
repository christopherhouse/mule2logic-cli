"""MockChatClient — test infrastructure for simulating LLM tool-calling.

This module provides :class:`MockChatClient`, a lightweight implementation of
the ``SupportsChatGetResponse`` protocol from the Microsoft Agent Framework.

When used as the ``client`` parameter to ``Agent(client=..., ...)``, it
simulates the LLM's tool-calling behaviour by **directly invoking** the
first available tool function and returning the result as an assistant
text message.

Because ``MockChatClient`` is not a ``BaseChatClient`` subclass, the MAF
``Agent`` does not apply the ``FunctionInvocationLayer`` middleware.
Instead, the mock calls the tool's underlying Python function itself and
wraps the return value in a ``ChatResponse``.

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
    Directly calls registered tool functions and returns their output as
    assistant text — no real LLM round-trip.
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

        Inspects the registered tools from *options*, calls the first
        tool function directly, and returns its result as an assistant
        text message.
        """
        self.call_count += 1

        # Extract tool objects (FunctionTool instances) from options
        tool_objects = self._extract_tool_objects(options)

        if tool_objects:
            # Call the first tool and return the result as text
            response = self._invoke_tool_and_respond(messages, tool_objects)
        else:
            # No tools — return a simple text response
            response = self._make_text_response(messages)

        if stream:
            return self._as_stream(response)
        return self._as_awaitable(response)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_tool_objects(options: Any | None) -> list[Any]:
        """Pull tool objects from the options dict passed by Agent."""
        if options is None:
            return []
        raw_tools = None
        if isinstance(options, dict):
            raw_tools = options.get("tools")
        elif hasattr(options, "get"):
            raw_tools = options.get("tools")  # type: ignore[union-attr]
        if not raw_tools:
            return []
        return list(raw_tools)

    @staticmethod
    def _invoke_tool_and_respond(
        messages: Sequence[Message],
        tool_objects: list[Any],
    ) -> ChatResponse[Any]:
        """Call the first tool's underlying function and return the result."""
        tool = tool_objects[0]

        # Build arguments from the user message context
        args = MockChatClient._infer_arguments_for_tool(tool, messages)

        # Invoke the tool's underlying callable
        func = getattr(tool, "func", None) or tool
        try:
            if callable(func):
                result_str = func(**args)
            else:
                result_str = json.dumps({"error": "Tool is not callable"})
        except Exception as exc:
            result_str = json.dumps({"error": str(exc)})

        # Return the tool result as an assistant text message
        response_msg = Message(role="assistant", contents=[str(result_str)])

        return ChatResponse(
            messages=[response_msg],
            response_id="mock-tool-response",
            finish_reason="stop",
        )

    @staticmethod
    def _make_text_response(messages: Sequence[Message]) -> ChatResponse[Any]:
        """Build a plain text ``ChatResponse`` when no tools are available."""
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
    def _infer_arguments_for_tool(
        tool: Any,
        messages: Sequence[Message],
    ) -> dict[str, Any]:
        """Build arguments for a tool call from the message context.

        Extracts ``input_path``, ``mode``, ``ir_json``, etc. from the
        user message so the deterministic tool functions receive real
        data to work with.
        """
        # Get the parameter schema
        params: dict[str, Any] = {}
        if hasattr(tool, "parameters") and callable(tool.parameters):
            try:
                params = tool.parameters()
            except Exception:
                params = {}

        user_text = ""
        for msg in reversed(list(messages)):
            if msg.role == "user" and msg.text:
                user_text = msg.text
                break

        args: dict[str, Any] = {}
        props = params.get("properties", {})

        for prop_name in props:
            if prop_name == "input_path":
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
                # Look for tool results from prior assistant messages
                for msg in messages:
                    if msg.role == "assistant" and msg.text:
                        # Previous tool output may contain IR-like data
                        args["ir_json"] = msg.text
                        break
                if "ir_json" not in args:
                    args["ir_json"] = "{}"
            elif prop_name == "output_directory":
                for line in user_text.split("\n"):
                    if "output directory:" in line.lower():
                        val = line.split(":", 1)[-1].strip()
                        if val != "default":
                            args["output_directory"] = val
                        break
            elif prop_name == "validation_report_json":
                args["validation_report_json"] = "[]"
            elif prop_name == "migration_gaps_json":
                args["migration_gaps_json"] = "[]"

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
