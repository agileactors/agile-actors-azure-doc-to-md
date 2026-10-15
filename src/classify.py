from __future__ import annotations
import anthropic

from pathlib import Path


from .prompts import CLASSIFY_PROMPT
from .config import MODEL_NAME

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "few_shot_examples"


def classify(raw_text: str) -> str:
    """
    Classify a document as "tree" or "narrative".

    Args:
        raw_text (str): The text to classify.

    Returns:
        str: "tree" or "narrative".
    """

    client = anthropic.Anthropic()
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


def load_few_shot_examples(category: str) -> list[tuple[str, str]]:
    """
    Load (raw, expected_json) few-shot pairs for a given category.

    Pairs are configuration, not code: adding a new example means
    dropping a `<name>_raw.txt` / `<name>_expected.json` pair into
    the matching folder, with no code changes required.

    Args:
        category (str): The category of examples to load.
    Returns:
        list[tuple[str, str]]: A list of (raw_text, expected_json)
    """
    category_dir = EXAMPLES_DIR / category
    pairs: list[tuple[str, str]] = []
    for raw_path in sorted(category_dir.glob("*_raw.txt")):
        expected_path = raw_path.with_name(
            raw_path.name.replace("_raw.txt", "_expected.json")
        )
        if not expected_path.exists():
            raise FileNotFoundError(
                f"Few-shot example '{raw_path.name}' has no matching "
                f"'{expected_path.name}'."
            )
        pairs.append(
            (
                raw_path.read_text(encoding="utf-8"),
                expected_path.read_text(encoding="utf-8"),
            )
        )
    return pairs
