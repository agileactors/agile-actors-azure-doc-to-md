import re

from .config import MIN_WORD_OVERLAP_RATIO
from .pydantic_schema import CallScript, flatten_attention_points

# The number of lines at the top of a document to search for a metadata line
_METADATA_SEARCH_LINES = 5

# The regex that matches the "Attention points" heading, which marks the end of the introduction body and the start of the attention_points list.
_ATTENTION_HEADING = re.compile(
    r"^#*\s*Attention points\s*$", re.MULTILINE | re.IGNORECASE
)

_METADATA_LINE = re.compile(r"^#*\s*Category:.*$", re.MULTILINE | re.IGNORECASE)
_ENTRY_POINT_TITLE = re.compile(r"\A\s*#*[^\n]*\n")


def sanity_check(script: CallScript, raw_text: str) -> list[str]:
    """
    Run all structural checks and return a list of warning strings.

    An empty list means the document passed every check. A non-empty
    list does not necessarily mean the mapping failed — it means a
    human should look at the flagged parts before trusting the output.

    Checks include:
        1. Narrative coverage: every sentence in the source document should be represented in the `main_text` field of the CallScript.
        2. Narrative size: `main_text` should not have more words than the source document's body.
        3. Dangling references: every branch in the CallScript should point to a valid step or outcome id.
        4. Unreachable outcomes: every outcome and non-entry step should be reachable from some branch in the CallScript.
        5. Ungrounded nodes: every step question and outcome title should match a line in the source document.
        6. Attention-point coverage: every line under the source's "Attention points" heading should be represented in `attention_points`.
        7. Shape conflict: a CallScript should not have both `steps` and `main_text` populated.

    Args:
        script (CallScript): The CallScript object to check.
        raw_text (str): The source document text, used to check narrative coverage.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    warnings: list[str] = []

    # Narrative-only checks
    if script.main_text:
        warnings.extend(_check_narrative_coverage(script, raw_text))
        warnings.extend(_check_narrative_size(script, raw_text))

    # Tree checks (no-ops on narratives, which have no steps or outcomes)
    warnings.extend(_check_dangling_references(script))
    warnings.extend(_check_unreachable_nodes_and_outcomes(script))
    warnings.extend(_check_grounding(script, raw_text))

    # Shape-agnostic checks
    warnings.extend(_check_attention_coverage(script, raw_text))

    # Shape-agnostic: this is a safety net for the case where a
    # CallScript bypasses the Pydantic validator
    warnings.extend(_check_shape_conflict(script))

    return warnings


def _check_dangling_references(script: CallScript) -> list[str]:
    """
    Flag any branch that points to an id that doesn't exist anywhere.

    Args:
        script (CallScript): The CallScript object to check.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    known_ids = {step.id for step in script.steps} | {
        outcome.id for outcome in script.outcomes
    }
    warnings = []
    for step in script.steps:
        for condition, target in step.branches.items():
            if target not in known_ids:
                warnings.append(
                    f"Dangling reference: step '{step.id}' branch "
                    f"'{condition}' points to undefined id '{target}'."
                )
    return warnings


def _check_unreachable_nodes_and_outcomes(script: CallScript) -> list[str]:
    """
    Flag outcomes and non-entry steps that nothing routes to.

    Args:
        script (CallScript): The CallScript object to check.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    referenced_ids: set[str] = set()
    for step in script.steps:
        referenced_ids.update(step.branches.values())

    warnings = []
    for outcome in script.outcomes:
        if outcome.id not in referenced_ids:
            warnings.append(
                f"Unreachable outcome: '{outcome.id}' ({outcome.title}) is "
                f"defined but no branch routes to it."
            )

    # The entry step is allowed to be unreachable, since it is the starting point of the script.
    entry_step_id = script.steps[0].id if script.steps else None
    for step in script.steps:
        if step.id != entry_step_id and step.id not in referenced_ids:
            warnings.append(
                f"Unreachable step: '{step.id}' is defined but no branch routes to it."
            )
    return warnings


def _check_grounding(script: CallScript, raw_text: str) -> list[str]:
    """
    Flag steps and outcomes whose wording doesn't appear in the source.

    Layout extraction keeps every box of a flowchart as its own line,
    so each step question and outcome title should match a single
    source line. Matching per line rather than against the whole
    document stops multi-word labels from passing on common words
    scattered elsewhere in the text. This catches nodes
    the model invented, e.g. an outcome made up to fill a dangling
    reference during repair.

    Args:
        script (CallScript): The CallScript object to check.
        raw_text (str): The source document text, used to check that each node exists.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    # Normalize and split the source text into lines
    source_lines = [set(_normalize(line).split()) for line in raw_text.splitlines()]
    # Create a list of (id, label) pairs for all steps and outcomes
    labels = [(step.id, step.question) for step in script.steps] + [
        (outcome.id, outcome.title) for outcome in script.outcomes
    ]

    warnings: list[str] = []
    for node_id, label in labels:
        label_words = set(_normalize(label).split())
        # if the label has no words, skip it
        if not label_words:
            continue
        # Find the best overlap ratio between the label and any source line
        best_overlap = max(
            (len(label_words & line) / len(label_words) for line in source_lines),
            default=0.0,
        )
        if best_overlap < MIN_WORD_OVERLAP_RATIO:
            warnings.append(
                f"Ungrounded node: '{node_id}' ({label!r}) does not match any "
                f"line in the source (best word overlap {best_overlap:.0%})."
            )
    return warnings


def _check_shape_conflict(script: CallScript) -> list[str]:
    """
    Flag the case where both tree and narrative fields are populated.

    The Pydantic validator on CallScript already prevents this at
    construction time; this check exists as a safety net for the case where a CallScript bypasses the validator.

    Args:
        script (CallScript): The CallScript object to check.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    if script.steps and script.main_text:
        return ["Shape conflict: both `steps` and `main_text` are populated."]
    return []


def _check_attention_coverage(script: CallScript, raw_text: str) -> list[str]:
    """
    Flag source attention-point lines that seem to have gone missing.

    Narrative coverage stops at the "Attention points" heading, and
    tree grounding only looks at steps and outcomes, so without this
    check a dropped caveat would pass silently. Each non-empty source
    line under the heading counts as covered if at least
    MIN_WORD_OVERLAP_RATIO of its distinct words appear in a single
    attention point, nested ones included.

    Args:
        script (CallScript): The CallScript object to check.
        raw_text (str): The source document text, used to find the attention-point lines.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    parts = _ATTENTION_HEADING.split(raw_text, maxsplit=1)
    # No "Attention points" heading in the source means nothing to cover
    if len(parts) < 2:
        return []

    point_words = [
        set(_normalize(point.text).split())
        for point in flatten_attention_points(script.attention_points)
    ]

    warnings: list[str] = []
    for line in parts[1].splitlines():
        line_words = set(_normalize(line).split())
        if not line_words:
            continue
        # Find the best overlap ratio between the line and any attention point
        best_overlap = max(
            (len(line_words & point) / len(line_words) for point in point_words),
            default=0.0,
        )
        if best_overlap < MIN_WORD_OVERLAP_RATIO:
            warnings.append(
                f"Possible missing attention point: source line not found in "
                f"attention_points (best word overlap {best_overlap:.0%}): "
                f"{line.strip()!r}"
            )
    return warnings


def _check_narrative_coverage(script: CallScript, raw_text: str) -> list[str]:
    """
    Flag source sentences that seem to have gone missing from main_text.

    A sentence counts as covered if at least MIN_WORD_OVERLAP_RATIO
    of its distinct normalized words also appear in ``main_text``.

    Args:
        script (CallScript): The CallScript object to check.
        raw_text (str): The source document text, used to check narrative coverage.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    source_sentences = _split_sentences(_extract_main_body(raw_text))
    output_words = set(_normalize(script.main_text).split())

    warnings: list[str] = []
    for sentence in source_sentences:
        sentence_words = set(_normalize(sentence).split())
        if not sentence_words:
            continue

        overlap = len(sentence_words & output_words) / len(sentence_words)
        if overlap < MIN_WORD_OVERLAP_RATIO:
            warnings.append(
                f"Possible missing content: source sentence not found in "
                f"main_text (word overlap {overlap:.0%}): {sentence.strip()!r}"
            )
    return warnings


def _check_narrative_size(script: CallScript, raw_text: str) -> list[str]:
    """
    Flag a main_text that has more words than the source body.

    Narrative coverage checks that every source sentence is represented in the output.
    This check flags cases where the model may have invented content.

    Args:
        script (CallScript): The CallScript object to check.
        raw_text (str): The source document text, used to measure the body's size.
    Returns:
        list[str]: A list of warning strings, empty if no issues were found.
    """
    # Wrap both bodies in a bare narrative CallScript so both sides are
    # measured by the same content_size property. The output is re-wrapped
    # too, so its attention points don't count against the body alone.
    source_body = _extract_main_body(raw_text)
    if source_body:
        source_size = CallScript(title="source", main_text=source_body).content_size
        output_size = CallScript(
            title="output", main_text=script.main_text
        ).content_size
        if output_size > source_size:
            return [
                (
                    f"Possible invented content: main_text has {output_size} "
                    f"words but the source body has only {source_size}."
                )
            ]
    return []


def _extract_main_body(raw_text: str) -> str:
    """
    Return just the narrative body of a source document.

    `main_text` holds the body alone — the title and category are
    their own fields, and the caveats are their own `attention_points`
    list. So coverage has to compare against the same slice.

    Args:
        raw_text (str): The source document text.
    Returns:
        str: The narrative body of the source document, with title and metadata stripped.
    """
    # Everything from the "Attention points" heading on belongs to
    # `attention_points`, not to the body.
    body = _ATTENTION_HEADING.split(raw_text)[0]

    # The search is restricted to the document header rather than run
    # over the whole body: a body that happens to contain the word
    # "Category:" in a later paragraph would otherwise have everything
    # above that paragraph silently cut away, and those sentences would
    # then never be coverage-checked at all.
    metadata_end = _header_metadata_end(body)
    if metadata_end is not None:
        return body[metadata_end:].strip()
    return _ENTRY_POINT_TITLE.sub("", body, count=1).strip()


def _header_metadata_end(body: str) -> int | None:
    """
    Offset just past the metadata line, or None if the header has none.

    It is used to strip the metadata line from the narrative body before coverage checking.
    If the metadata line is not found in the first _METADATA_SEARCH_LINES lines, it is assumed that
    the document has no metadata line. Otherwise, the offset returned is the index of the first character
    after the metadata line in order to exclude it from the narrative body.

    Args:
        body (str): The source document text, with attention points stripped.
    Returns:
        int | None: The offset just past the metadata line, or None if the header has
    """
    offset = 0
    for _ in range(_METADATA_SEARCH_LINES):
        line_end = body.find("\n", offset)
        line = body[offset:] if line_end == -1 else body[offset:line_end]
        if _METADATA_LINE.match(line):
            return len(body) if line_end == -1 else line_end + 1
        if line_end == -1:
            return None
        offset = line_end + 1
    return None


def _split_sentences(text: str) -> list[str]:
    """
    Split the text into sentences based on punctuation.
    Args:
        text (str): The text to split into sentences.
    Returns:
        list[str]: A list of sentences extracted from the text.
    """
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def _normalize(text: str) -> str:
    """
    Lowercase and strip punctuation for fuzzy word-overlap comparison.
    Args:
        text (str): The text to normalize.
    Returns:
        str: The normalized text.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
