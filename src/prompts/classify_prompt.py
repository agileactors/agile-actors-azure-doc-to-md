CLASSIFY_PROMPT = """\
You will be shown the raw text of a customer-support call script, as
extracted from a Word document.

Decide whether it is:
- "tree": a decision flowchart. After extraction, its boxes appear as short
  lines in reading order, usually `##` headings, with bare answer lines such
  as "Yes" and "No" between the questions. Choose this only if there is at
  least one explicit question with more than one answer leading somewhere
  different.
- "narrative": prose read top to bottom. Conditional sentences inside the
  prose ("If the customer..., then...") do not make it a tree.

Respond with exactly one word: tree or narrative.
"""
