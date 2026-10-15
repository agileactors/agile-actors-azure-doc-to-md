from __future__ import annotations
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "few_shot_examples"


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
