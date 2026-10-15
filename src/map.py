import anthropic

from .classify import load_few_shot_examples
from .config import MODEL_NAME
from .prompts import AGENT_PROMPT
from .pydantic_schema import CallScript


def map_to_schema(raw_text: str, category: str) -> CallScript:
    """
    Map raw text into a validated CallScript.


    Args:
        raw_text (str): The raw text to map.
        category (str): The category of the document, used to load few-shot examples.
    Returns:
        CallScript: The validated CallScript object.
    """
    client = anthropic.Anthropic()
    few_shot = load_few_shot_examples(category)
    print(f"few_shot={len(few_shot)} examples for category {category}")

    messages = []
    for example_raw, example_expected in few_shot:
        # The few-shot examples are added to the prompt as a series of user/assistant messages.
        messages.append({"role": "user", "content": example_raw})
        messages.append({"role": "assistant", "content": example_expected})
    # The actual document is added as the final user message.
    messages.append({"role": "user", "content": raw_text})

    # The tool's `input_schema` is the Pydantic model's JSON schema, which
    # forces the model to produce a valid CallScript object.
    tool = {
        "name": "record_call_script",
        "description": (
            "Record the CallScript structure extracted from the source text."
        ),
        "input_schema": CallScript.model_json_schema(),
    }

    response = client.messages.create(
        model=MODEL_NAME,
        # A full CallScript (steps, outcomes, attention points) can be large,
        # so max_tokens needs enough headroom for the whole structured object.
        max_tokens=16000,
        system=AGENT_PROMPT,
        messages=messages,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_call_script"},
    )

    tool_call = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_call is None:
        raise ValueError(f"No tool_use block (stop_reason={response.stop_reason!r})")

    # Validate the tool's input against the Pydantic model
    return CallScript.model_validate(tool_call.input)
