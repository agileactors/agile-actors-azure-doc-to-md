from __future__ import annotations

from functools import lru_cache

import anthropic

from .config import MODEL_NAME
from .pydantic_schema import CallScript

# A full CallScript (steps, outcomes, attention points) can be large, and the
# whole object comes back as tool input, so this needs enough headroom.
CALL_SCRIPT_MAX_TOKENS = 16000

_TOOL_NAME = "record_call_script"


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    """
    Return the shared Anthropic client, created on first use.

    Created lazily rather than at import time, so the credentials loaded
    from `environment/.env` are already in place when it is built.

    Returns:
        anthropic.Anthropic: The shared client.
    """
    return anthropic.Anthropic()


def request_call_script(
    system: str,
    messages: list[dict],
    tool_description: str,
) -> CallScript:
    """
    Ask the model for a CallScript via forced tool use and validate it.

    The tool's `input_schema` is the Pydantic model's JSON schema, and
    `tool_choice` forces the model to call it, so the reply is always a
    structured object rather than free text.

    Args:
        system (str): The system prompt for this stage.
        messages (list[dict]): The conversation to send, ending with a user message.
        tool_description (str): What the tool records, shown to the model.
    Returns:
        CallScript: The validated CallScript object.
    """
    client = get_client()
    tool = {
        "name": _TOOL_NAME,
        "description": tool_description,
        "input_schema": CallScript.model_json_schema(),
    }

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=CALL_SCRIPT_MAX_TOKENS,
        system=system,
        messages=messages,
        tools=[tool],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )

    if response.stop_reason in ("max_tokens", "refusal"):
        raise ValueError(
            f"Model stopped early (stop_reason={response.stop_reason!r}); "
            f"no complete CallScript was returned."
        )

    tool_call = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_call is None:
        raise ValueError(f"No tool_use block (stop_reason={response.stop_reason!r})")

    # Validate the tool's input against the Pydantic model
    return CallScript.model_validate(tool_call.input)
