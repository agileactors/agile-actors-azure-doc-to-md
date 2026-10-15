from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Outcome(BaseModel):
    """
    A terminal result of a call flow (a leaf node).

    An Outcome always has at least one branch pointing into it and
    zero branches pointing out of it. If content routes onward, it
    belongs in a DecisionStep instead.
    """

    # Required fields are marked with `...` to ensure Pydantic enforces their presence.
    id: str = Field(..., description="Unique outcome id, e.g. 'OUTCOME_1'.")
    title: str = Field(
        ...,
        description="Short label for the outcome, worded as in the source box.",
    )
    description: str = Field(
        ...,
        description=(
            "What the agent does at this outcome, in the source box's own "
            "words. Restate only that box — never add a reason, condition, "
            "or detail the source does not state."
        ),
    )


class DecisionStep(BaseModel):
    """
    A single branching question in a call-flow decision tree.

    A DecisionStep must route somewhere for every branch it defines.
    Never collapse a chain of distinct questions into a single step,
    even when every branch of that chain ends at the same outcome.
    """

    id: str = Field(..., description="Unique step id, e.g. 'STEP_1'.")
    question: str = Field(..., description="The question the agent must answer.")
    branches: dict[str, str] = Field(
        ...,
        description=(
            "Mapping of answer label (e.g. 'yes', 'no', 'unconfirmed') to "
            "the id of the next DecisionStep or Outcome. Never point a "
            "branch at an id that is not defined elsewhere in the document."
        ),
    )


class AttentionPoint(BaseModel):
    """
    A warning or caveat, possibly with nested sub-points.
    """

    text: str = Field(
        ..., description="The caveat text, exactly as worded in the source."
    )
    children: list[AttentionPoint] = Field(
        default_factory=list,
        description="Sub-points nested under this one, if the source implies any.",
    )


class CallScript(BaseModel):
    """
    A CallScript describes either a decision-tree call flow or a
    plain-narrative procedure, never both.

    Exactly one of (`steps`) or (`main_text`) must be populated,
    never both and never neither. That single constraint is what
    lets two structurally different source documents share one
    schema and one render template.
    """

    title: str = Field(..., description="The name of the procedure.")
    category: str | None = Field(
        default=None,
        description="High-level grouping, e.g. 'Billing', 'Technical Support'.",
    )
    attention_points: list[AttentionPoint] = Field(
        default_factory=list,
        description=(
            "Warnings or caveats the agent must not miss, preserved in the "
            "order and nesting they appeared in the source document."
        ),
    )

    # Decision-tree shape
    steps: list[DecisionStep] = Field(default_factory=list)
    outcomes: list[Outcome] = Field(default_factory=list)

    # Plain-narrative shape
    main_text: str | None = Field(
        default=None,
        description="Free-form procedure text, used for non-tree documents.",
    )

    @model_validator(mode="after")
    def check_single_shape(self) -> CallScript:
        """Enforce that a document is a tree OR a narrative, never both."""
        is_tree = bool(self.steps)
        is_narrative = bool(self.main_text)

        if is_tree and is_narrative:
            raise ValueError(
                "A CallScript cannot have both `steps` and `main_text` set — "
                "pick one shape."
            )
        if not is_tree and not is_narrative:
            raise ValueError(
                "A CallScript must have either `steps` or `main_text` set."
            )
        return self

    @property
    def content_size(self) -> int:
        """
        Rough size metric used to detect a repair that deletes content.

        Counts steps, outcomes, and branches for trees, words for
        narratives, and attention points (nested ones included) for
        both, so removing any of them lowers the total.
        """
        branch_count = sum(len(step.branches) for step in self.steps)
        narrative_words = len(self.main_text.split()) if self.main_text else 0
        # flatten_attention_points counts every point, including nested ones,
        # so we don't need to count children separately.
        attention_count = len(flatten_attention_points(self.attention_points))
        return (
            len(self.steps)
            + len(self.outcomes)
            + branch_count
            + narrative_words
            + attention_count
        )


def flatten_attention_points(points: list[AttentionPoint]) -> list[AttentionPoint]:
    """
    Return every attention point in depth-first order, children included.
    Args:
        points (list[AttentionPoint]): The list of attention points to flatten.
    Returns:
        list[AttentionPoint]: A flat list of all attention points, including nested ones.
    """
    flat: list[AttentionPoint] = []
    for point in points:
        # Expand each point into the flat list, then recursively flatten its children.
        flat.append(point)
        flat.extend(flatten_attention_points(point.children))
    return flat
