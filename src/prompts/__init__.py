"""System prompts, kept as data so each stage imports one name.

Each prompt lives in its own module; this package re-exports them so
callers write `from .prompts import CLASSIFY_PROMPT` rather than
reaching into the individual files.
"""

from .agent_prompt import AGENT_PROMPT
from .classify_prompt import CLASSIFY_PROMPT
from .repair_prompt import REPAIR_SYSTEM_PROMPT

__all__ = ["AGENT_PROMPT", "CLASSIFY_PROMPT", "REPAIR_SYSTEM_PROMPT"]
