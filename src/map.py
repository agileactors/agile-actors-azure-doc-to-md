import anthropic

from .examples import load_few_shot_examples
from .llm import request_call_script
from .prompts import AGENT_PROMPT
from .pydantic_schema import CallScript


def map_to_schema(
    raw_text: str, category: str, client: anthropic.Anthropic | None = None
) -> CallScript:
    """
    Map raw text into a validated CallScript.


    Args:
        raw_text (str): The raw text to map.
        category (str): The category of the document, used to load few-shot examples.
        client (anthropic.Anthropic | None): Client to use; the shared one if omitted.
    Returns:
        CallScript: The validated CallScript object.
    """
    few_shot = load_few_shot_examples(category)
    print(f"few_shot={len(few_shot)} examples for category {category}")

    messages = []
    for example_raw, example_expected in few_shot:
        # The few-shot examples are added to the prompt as a series of user/assistant messages.
        messages.append({"role": "user", "content": example_raw})
        messages.append({"role": "assistant", "content": example_expected})
    # The actual document is added as the final user message.
    messages.append({"role": "user", "content": raw_text})

    return request_call_script(
        system=AGENT_PROMPT,
        messages=messages,
        tool_description="Record the CallScript structure extracted from the source text.",
        client=client,
    )
