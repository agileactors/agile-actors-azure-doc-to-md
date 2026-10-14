# Turning messy docs into structured Markdown

Word documents go in, structured Markdown comes out — with a deterministic
validator between the language model and the file it writes.

This is the companion code for [`article.md`](article.md), which walks through
the same pipeline in detail. This README covers what it does and why.

## The problem

Procedures get written in two shapes: **decision trees**, usually drawn as a
flowchart, and **plain narratives**, just prose. Both carry detail nobody can
afford to lose — deadlines, escalation rules, caveats. Feeding a stack of them to
an AI application means getting both into one predictable format, without
dropping or inventing a word.

The hard part is that layout extraction **reads boxes but not arrows**. A
flowchart comes back as a flat list of labels in reading order. Every box
survives; the topology — which is the entire content of a decision tree — does
not. Here is what Azure returns for a password-reset flowchart:

```
## Identity verified via standard two-way authenticator?
## No
## Yes
## Reject the request
## Suspicious activity detected on the account?
...
```

Nine flat lines, all at the same heading level. Which `Yes` belongs to which
question, and where either one leads, is gone. Rebuilding that is the pipeline's
actual job — and the reason the validation and repair stages exist.

Here is the same document after a run:

```markdown
## Call flow

**STEP_1.** Identity verified via standard two-way authenticator?
- If **no** → `OUTCOME_1`
- If **yes** → `STEP_2`

**STEP_2.** Suspicious activity detected on the account?
- If **yes** → `OUTCOME_2`
- If **no** → `OUTCOME_3`

## Outcomes

- **OUTCOME_1** (Reject the request): Reject the request
- **OUTCOME_2** (Inform the Security Team): Inform the Security Team
- **OUTCOME_3** (Password reset link sent): Password reset link sent
```

The structure is reconstructed. The wording is not touched — every label above
appears verbatim in the source.

## How it works

| Stage | What it does | File |
|---|---|---|
| **Extract** | `.docx` → text and layout, via Azure Document Intelligence `prebuilt-layout` | `src/extract.py` |
| **Classify** | tree or narrative — picks which few-shot examples to show the model | `src/classify.py` |
| **Map** | text + examples → a `CallScript` object, via Claude forced tool-use | `src/map.py` |
| **Validate** | deterministic structural checks, no LLM involved | `src/validate.py` |
| **Repair** | one gated attempt, only if validation flagged something | `src/repair.py` |
| **Render** | `CallScript` → Markdown, via a single Jinja2 template | `src/render.py` |

**The design idea is that no stage trusts the one before it.**

A single Pydantic model, `CallScript`, holds both shapes — tree fields (`steps`,
`outcomes`) and the narrative field (`main_text`) — with a validator enforcing
that exactly one is filled. That one constraint is what lets two very different
documents share a schema and a render template.

But a schema only checks shape, not sense. A model can return a perfectly valid
object whose branches point at steps that were never defined. So after mapping,
plain Python checks the graph: dangling references, steps or outcomes nothing routes to,
steps or outcomes whose wording matches no line in the source, and — for
narratives — whether every source sentence actually made it into `main_text`
and whether `main_text` is no longer than the source body. For both shapes, it
checks that every attention point in the source made it into the output. No LLM,
no tokens, same answer every time.

If something is flagged, the model gets **exactly one** attempt to fix it, and
that attempt has to earn its place. The cheapest way to "fix" a branch pointing
nowhere is to delete the branch, so a repair is kept only if it both lowers the
warning count **and** leaves the document no smaller. Otherwise the original
stands and the warnings are written out for a human.

The goal was never a pipeline that always gets it right. It's one that tells you
when it might not have.

## Running it

Requires **Python 3.12+** and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/agileactors/agile-actors-azure-doc-to-md.git
cd agile-actors-azure-doc-to-md
uv sync

cp environment/.env.example environment/.env   # then fill in all three values

uv run main.py
```

Credentials live in **`environment/.env`**, not a root-level `.env` — you need an
[Azure Document Intelligence
resource](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
and an [Anthropic API key](https://console.anthropic.com/). There is no offline
mode; `main.py` checks for all three up front and names anything missing.

Two documents ship in `sample_inputs/`, so this runs out of the box. Each one
gets a folder in `outputs/<name>/`:

| File | Contents |
|---|---|
| `final.md` | the rendered Markdown |
| `raw.txt` | the extracted source text, for diffing |
| `warnings.txt` | surviving warnings, or `No warnings - all checks passed.` |

`warnings.txt` is written even when nothing was flagged, so "no warnings" is a
recorded fact rather than a missing file you have to interpret. One document
failing doesn't stop the batch.

Cost per document: one Azure call, one classification call, one mapping call, and
a repair call only if validation flagged something. The model is named in one
place, `src/config.py`.

## Using your own documents

Drop any `.docx` into `sample_inputs/` and run again.

For better results on a new kind of document, add a few-shot example: a
`<name>_raw.txt` (the extracted text) and a `<name>_expected.json` (what it
should map to, written by hand) in `few_shot_examples/tree/` or
`few_shot_examples/narrative/`. The pipeline picks up new pairs automatically,
and fails loudly if one half is missing.

To get the `_raw.txt`, put the `.docx` in `synthetic_docs/docs/trees/` or
`synthetic_docs/docs/narratives/` and run:

```bash
uv run src/create_few_shot_examples/create_raw_examples.py
```

It runs every document there through the same Azure extraction the pipeline
uses and writes the result into the matching `few_shot_examples/` folder. If a
`_expected.json` already exists, it also validates it and renders a `<name>.md`
preview so you can review the pair. Each run re-extracts every document (one
Azure call each) and overwrites the existing `_raw.txt` files.

Keep the two worlds separate. `sample_inputs/` is deliberately *not* part of the
example corpus — if a demo input is also an example, the model is handed its own
answer and the output tells you nothing.

## What it doesn't do

- **It is bounded by extraction.** Nothing downstream can recover a label that
  never came back.
- **Validation checks structure, not meaning.** A branch pointed at the *wrong*
  existing outcome is invisible to a graph check.
- **Narrative checks are fuzzy.** A source sentence counts as covered when 80%
  of its distinct words appear in `main_text`, so a sentence can lose a few words
  and still pass, and those spare words leave room for a short invented phrase
  under the size limit.
- **One repair attempt**, then the warnings are surfaced rather than retried.


## Layout

```
main.py                 # batch orchestrator — the entry point
src/                    # one module per stage, plus:
  pydantic_schema.py    #   CallScript, DecisionStep, Outcome, AttentionPoint
  prompts/              #   one prompt per stage
templates/              # the single Jinja2 template, both shapes
few_shot_examples/      # what the model is shown at mapping time
sample_inputs/          # what the demo processes — held out of the corpus
synthetic_docs/         # the source .docx files the examples came from
outputs/                # generated on each run
environment/            # credentials: copy .env.example to .env here
```

The stages in `src/` are independent and importable on their own — `main.py` only
chains them together and writes the results.

## License

[MIT](LICENSE) — free to use, including commercially.
