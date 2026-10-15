from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / "environment" / ".env"
SAMPLE_INPUTS_DIR = PROJECT_ROOT / "sample_inputs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EXAMPLES_DIR = PROJECT_ROOT / "few_shot_examples"
SYNTHETIC_DOCS_DIR = PROJECT_ROOT / "synthetic_docs" / "docs"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Newer models (claude-sonnet-5-5, claude-opus-5-5) reject two things this
# pipeline relies on: thinking={"type": "disabled"} and the forced tool_choice.
# Both return a 400 error, so switching to one of them means changing those calls as well.
MODEL_NAME = "claude-sonnet-5"

# A full CallScript (steps, outcomes, attention points) can be large, and the
# whole object comes back as tool input, so this needs enough headroom.
CALL_SCRIPT_MAX_TOKENS = 16000

# Suffixes of source documents the pipeline has been tested on.
SOURCE_SUFFIXES = (".docx",)
# Suffixes create_raw_examples.py extracts; .pdf works but no example uses it.
EXAMPLE_SOURCE_SUFFIXES = (".docx", ".pdf")

# The minimum fraction of distinct words in a source sentence that must also appear in the `main_text` for it to count as "covered" by the narrative.
# The same ratio decides whether a step or outcome label matches a source line, and whether a source attention-point line is covered by `attention_points`.
MIN_WORD_OVERLAP_RATIO = 0.8
