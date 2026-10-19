from .llm import request_call_script
from .load_examples import load_few_shot_examples
from .prompts import AGENT_PROMPT
from .pydantic_schema import CallScript


def map_to_schema(raw_text: str, category: str) -> CallScript:
    """
    Map raw text into a validated CallScript.

    Args:
        raw_text (str): The raw text to map.
        category (str): The document's shape, "tree" or "narrative", used to pick the few-shot examples.
    Returns:
        CallScript: The validated CallScript object.
    """
    few_shot = load_few_shot_examples(category)
    print(f"few_shot={len(few_shot)} examples for category {category}")

    messages = []
    for example_raw, example_expected in few_shot:
        # Each example becomes a user turn (its extracted text) and an
        # assistant turn (its hand-written CallScript), as a worked answer.
        messages.append({"role": "user", "content": example_raw})
        messages.append({"role": "assistant", "content": example_expected})
    # The document to map goes last: the user turn the model must answer.
    messages.append({"role": "user", "content": raw_text})

    # Forced tool use: Claude must return a CallScript, which is then validated.
    # An incomplete reply raises an error.
    return request_call_script(
        system=AGENT_PROMPT,
        messages=messages,
        tool_description="Record the CallScript structure extracted from the source text.",
    )
