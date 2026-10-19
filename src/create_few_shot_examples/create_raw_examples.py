import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    ENV_FILE,
    EXAMPLES_DIR,
    SOURCE_SUFFIXES,
    SYNTHETIC_DOCS_DIR,
)
from src.extract import extract_text
from src.pydantic_schema import CallScript

load_dotenv(ENV_FILE)


# synthetic_docs/docs/<folder> -> classify label used as the few_shot_examples/ folder name
CATEGORY_BY_FOLDER = {
    "narratives": "narrative",
    "trees": "tree",
}


def create_raw_example(docx_path: str | Path, shape_category: str, name: str) -> Path:
    """Extract a .docx or .pdf and save it as a few-shot raw-text example.

    Writes to `few_shot_examples/<category>/<name>_raw.txt`. A matching
    `<name>_expected.json` still needs to be written by hand next to
    it — `load_few_shot_examples()` raises if that partner is missing.


    Steps:
        1. Extract text from the .docx or .pdf file.
        2. Create the category folder under `few_shot_examples/` if it doesn't exist.
        3. Write the raw text to `<name>_raw.txt` in that folder.
        4. If `<name>_expected.json` already exists, validate it against `CallScript`.

    Args:
        docx_path: path to a .docx or .pdf file to extract text from
        shape_category: name of the shape category folder to create under `few_shot_examples/` (e.g., "tree" or "narrative")
        name: base name for the raw example file (without suffix)

    Returns:
        Path to the raw example file that was created.
    """
    docx_path = Path(docx_path)
    docx_name = docx_path.name
    # Extract using Azure Document Intelligence
    print(f"Extracting text from {docx_name}...")
    raw_text = extract_text(docx_path)

    category_dir = EXAMPLES_DIR / shape_category
    category_dir.mkdir(parents=True, exist_ok=True)

    # Write the raw text to a file named <name>_raw.txt in the category folder
    raw_path = category_dir / f"{name}_raw.txt"
    raw_path.write_text(raw_text, encoding="utf-8")
    raw_name = raw_path.name
    print(f"Wrote raw text to {raw_name}")

    # Expected files are not generated automatically; they must be created manually
    expected_path = raw_path.with_name(f"{name}_expected.json")
    if not expected_path.exists():
        print(
            f"WARNING: expected output file {expected_path} does not exist yet. "
            f"You will need to create it by hand before running the few-shot demo."
        )
        return raw_path

    # Validate the hand-written expected JSON
    CallScript.model_validate_json(expected_path.read_text(encoding="utf-8"))

    return raw_path


def create_raw_examples_from_synthetic_docs() -> list[Path]:
    """
    Extract every synthetic document into its `few_shot_examples/` folder.

    Returns:
        Paths of the raw example files that were created.
    """
    raw_paths: list[Path] = []
    for folder, category in CATEGORY_BY_FOLDER.items():
        source_dir = SYNTHETIC_DOCS_DIR / folder
        if not source_dir.is_dir():
            print(f"WARNING: {source_dir} does not exist, skipping.")
            continue

        for doc_path in sorted(source_dir.iterdir()):
            # Check the suffix to avoid trying to extract from non-docx/pdf files (e.g., .png images of the trees)
            if doc_path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            # Create a raw example for each document, using the stem of the filename as the base name
            raw_path = create_raw_example(doc_path, category, doc_path.stem)
            print(f"Created raw example for {doc_path.name}")
            raw_paths.append(raw_path)
            print(50 * "-")

    return raw_paths


if __name__ == "__main__":
    created = create_raw_examples_from_synthetic_docs()
    print(f"Created {len(created)} raw example(s) under {EXAMPLES_DIR}")
