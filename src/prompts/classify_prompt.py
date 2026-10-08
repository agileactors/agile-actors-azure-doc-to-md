CLASSIFY_PROMPT = """\
You will be shown the raw text of a customer-support call script.

Decide whether it is:
- "tree": the document branches based on questions/answers and routes
  the agent to different steps or outcomes.
- "narrative": the document is prose instructions with no branching
  logic, only explanatory text.

Respond with exactly one word: tree or narrative.
"""
