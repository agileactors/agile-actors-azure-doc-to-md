"""
Batch orchestrator for the call-flow structuring demo.

For every document under `sample_inputs/` (searched recursively), this
always writes three outputs to `outputs/<name>/`, where `<name>` mirrors
the document's path under `sample_inputs/` without its suffix:

- `final.md`      the rendered Markdown
- `raw.txt`       the normalized source text, for diffing
- `warnings.txt`  written even when empty, so its presence never has
                   to be inferred — "no warnings" is a fact, not a gap

A document that fails gets only `error.txt` instead, and files from an
earlier run are removed first so nothing stale is left behind.

A short summary is printed at the end, naming any document that was flagged or that failed.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.classify import classify
from src.config import ENV_FILE, OUTPUTS_DIR, SAMPLE_INPUTS_DIR, SOURCE_SUFFIXES
from src.extract import extract_text
from src.map import map_to_schema
from src.render import render_markdown
from src.repair import attempt_repair
from src.validate import sanity_check

load_dotenv(ENV_FILE)


# Every file a run can leave in `outputs/<name>/`; `error.txt` only on failure.
OUTPUT_FILES = ("final.md", "raw.txt", "warnings.txt", "error.txt")


def process_file(source_path: Path) -> tuple[str, list[str], str]:
    """Run one file through the full pipeline.

    Steps:
        1. Extract normalized text from the source document.
        2. Classify the text into a schema category.
        3. Map the text to a structured schema.
        4. Sanity-check the schema for common issues.
        5. Attempt to repair the schema if any issues were found.


    Returns:
        A tuple of (final_markdown, final_warnings, raw_text). `raw_text` is
        handed back rather than re-extracted by the caller, because for
        a `.docx` a second extraction is a second billable Azure call.
    """

    # Step 1: Extract normalized text from the source document.
    print("Extracting text...")
    raw_text = extract_text(source_path)

    # Step 2: Classify the text into a schema category.
    print("Classifying the text...")
    category = classify(raw_text)

    # Step 3: Map the text to a structured schema.
    print("Mapping onto CallScript...")
    script = map_to_schema(raw_text, category)

    # Step 4: Sanity-check the schema for common issues.
    print("Validating...")
    warnings = sanity_check(script, raw_text)
    if not warnings:
        print("Validation passed, no repair needed")
    else:
        print(f"Validation found {len(warnings)} warning(s):")

        # if any warnings were found, attempt to repair the schema.
        print("Repair needed, attempting one gated repair...")
        script, warnings, repaired = attempt_repair(script, warnings, raw_text)
        if repaired:
            print(f"Repair accepted for {source_path.name}")
        else:
            print("Repair rejected, keeping the original object")

    # Step 5: Render the schema to Markdown.
    print("Rendering Markdown...")
    final_markdown = render_markdown(script)
    print(50 * "-")

    return final_markdown, warnings, raw_text


REQUIRED_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
    "AZURE_DOCUMENT_INTELLIGENCE_KEY",
)


def check_credentials() -> None:
    """
    Fail up front if a credential is missing.
    """
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise SystemExit(
            "Missing credential(s): "
            + ", ".join(missing)
            + f"\nSet them in {ENV_FILE} "
            "(copy environment/.env.example to start)."
        )


def run_batch() -> None:
    """Process every sample input file, write outputs, and print a summary."""
    check_credentials()
    OUTPUTS_DIR.mkdir(exist_ok=True)

    processed = 0
    flagged: list[str] = []
    failed: list[str] = []

    source_paths = sorted(
        path
        for path in SAMPLE_INPUTS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
    )
    if not source_paths:
        print(f"No source documents found under {SAMPLE_INPUTS_DIR}.")

    for source_path in source_paths:
        relative_name = source_path.relative_to(SAMPLE_INPUTS_DIR).with_suffix("")
        stem = relative_name.as_posix()
        file_output_dir = OUTPUTS_DIR / relative_name
        file_output_dir.mkdir(parents=True, exist_ok=True)

        # Clear the previous run's files first to avoid leaving stale outputs behind.
        for name in OUTPUT_FILES:
            (file_output_dir / name).unlink(missing_ok=True)

        print(f"Processing {source_path.name}...")
        try:
            final_markdown, warnings, raw_text = process_file(source_path)
        except Exception as exc:  # noqa: BLE001 - batch must not die on one file
            failed.append(stem)
            print(f"  FAILED: {exc}")
            (file_output_dir / "error.txt").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
            )
            continue

        (file_output_dir / "final.md").write_text(final_markdown, encoding="utf-8")
        (file_output_dir / "raw.txt").write_text(raw_text, encoding="utf-8")

        if warnings:
            warnings_text = "\n".join(f"- {warning}" for warning in warnings)
            flagged.append(stem)
        else:
            warnings_text = "No warnings - all checks passed."

        (file_output_dir / "warnings.txt").write_text(
            warnings_text + "\n", encoding="utf-8"
        )
        processed += 1
        print(f"Warnings found: {len(warnings)} warning(s)")
        print("\n")

    # `processed` counts every file that produced output, flagged ones
    # included — a flagged document still rendered.
    print(f"\nBatch complete: {processed} processed, {len(failed)} failed")
    if flagged:
        print(f"  flagged: {', '.join(flagged)}")
    if failed:
        print(f"  failed:  {', '.join(failed)}")


if __name__ == "__main__":
    run_batch()
