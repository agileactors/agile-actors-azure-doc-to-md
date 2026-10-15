from __future__ import annotations
import anthropic

from .prompts import CLASSIFY_PROMPT
from .config import MODEL_NAME
from .llm import get_client


def classify(raw_text: str, client: anthropic.Anthropic | None = None) -> str:
    """
    Classify a document as "tree" or "narrative".

    Args:
        raw_text (str): The text to classify.
        client (anthropic.Anthropic | None): Client to use; the shared one if omitted.

    Returns:
        str: "tree" or "narrative".
    """

    client = client or get_client()
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=16,  # Keep it short, we only need a label.
        thinking={"type": "disabled"},
        system=CLASSIFY_PROMPT,  # Tells the model how to classify.
        messages=[{"role": "user", "content": raw_text}],
    )

    # _first_text extracts the first text block from the response, which should contain the label.
    label = _first_text(response).strip().lower()
    print(f"Label is {label!r}")
    return "tree" if "tree" in label else "narrative"


def _first_text(response) -> str:
    """
    Extract the first text block from a response.

    Args:
        response: The response object from the API.

    Returns:
        str: The text content of the first text block.
    """
    for block in response.content:
        if block.type == "text":
            return block.text
    raise ValueError(
        f"No text block in response (stop_reason={response.stop_reason!r}, "
        f"blocks={[block.type for block in response.content]})."
    )
