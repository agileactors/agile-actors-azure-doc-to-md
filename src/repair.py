from __future__ import annotations
import anthropic

from .prompts import REPAIR_SYSTEM_PROMPT
from .pydantic_schema import CallScript
from .validate import sanity_check
from .config import MODEL_NAME


def attempt_repair(
    script: CallScript, warnings: list[str], raw_text: str
) -> tuple[CallScript, list[str], bool]:
    """
    Attempt exactly one repair call and apply the acceptance gate.

    Steps:
        1. Call the LLM to repair the flagged warnings.
        2. Run the same sanity checks on the repaired script.
        3. Accept the repair if it reduces the number of warnings and preserves content size.

    Args:
        script (CallScript): The original CallScript object.
        warnings (list[str]): The list of warnings to fix.
        raw_text (str): The source document text, used to restore missing content.
    Returns:
        A tuple of (final_script, final_warnings, was_repair_accepted).
        If the repair is rejected, `script` and `warnings` are returned
        unchanged, along with `False`.
    """
    if not warnings:
        return script, warnings, False

    candidate = llm_repair(script, warnings, raw_text)
    candidate_warnings = sanity_check(candidate, raw_text)

    warnings_improved = len(candidate_warnings) < len(warnings)
    size_preserved = candidate.content_size >= script.content_size

    if warnings_improved and size_preserved:
        return candidate, candidate_warnings, True

    # Repair made things worse or smaller — reject it, keep the original.
    return script, warnings, False


def llm_repair(script: CallScript, warnings: list[str], raw_text: str) -> CallScript:
    """
    Call the LLM to repair a CallScript object.

    Args:
        script (CallScript): The mapped CallScript object to repair.
        warnings (list[str]): The list of warnings to fix.
        raw_text (str): The source document text, used to restore missing content.
    Returns:
        CallScript: The repaired CallScript object returned by the LLM.
    """

    client = anthropic.Anthropic()
    warning_text = "\n".join(f"- {warning}" for warning in warnings)
    user_message = (
        f"Source document:\n{raw_text}\n\n"
        f"Current object:\n{script.model_dump_json(indent=2)}\n\n"
        f"Warnings to fix:\n{warning_text}"
    )

    tool = {
        "name": "record_call_script",
        "description": "Record the repaired CallScript structure.",
        "input_schema": CallScript.model_json_schema(),
    }

    response = client.messages.create(
        model=MODEL_NAME,
        # Same budget note as the mapping call: thinking + tool input share it.
        max_tokens=16000,
        system=REPAIR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_call_script"},
    )
    tool_call = next(block for block in response.content if block.type == "tool_use")
    return CallScript.model_validate(tool_call.input)
