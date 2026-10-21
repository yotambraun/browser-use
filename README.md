# Evidence: browser-use#6106 against the #6068 bypass

Pre-registered test of [browser-use#6106](https://github.com/browser-use/browser-use/pull/6106) (head `71da6df`)
against its merge base on main (`ccd22fe`), using the repro from
[browser-use#6068](https://github.com/browser-use/browser-use/issues/6068). The protocol was committed (`0c0896c`)
before any measurement; results came in a later commit.

## Result in one table

`/bypass` page (the button never enables), gpt-4.1-mini, 10 runs per build:

| | main `ccd22fe` | #6106 |
|---|---|---|
| Order placed | 9 | 10 |
| `is_successful()` True | 9 | 10 |
| Warning shown to the agent | 0 | 10 |
| Order placed, success True, bypass not clearly stated | 2 | 8 |

The warning detects direct `disabled`/`readOnly` writes, but the agent kept going. No over-blocking on the two
legitimate pages (6/6 for both builds). Full results, the pre-registered decision rules and notes: [RESULTS.md](RESULTS.md).

## Files

- `PROTOCOL.md`: the plan, predictions and decision rules, committed before any measurement.
- `RESULTS.md`: results against each decision rule, and after-data notes, including one wrong prediction.
- `RUBRIC.md`: how final messages are labeled for disclosure, blind to the build.
- `pages.py`: the local pages (bypass, legitimate with a 1.5 s delay, legitimate with no delay, CSP pages).
- `mechanism.py`: deterministic check of the `evaluate` action, no LLM. `csp_validity.py`: after-data check of the CSP pages.
- `trial.py`, `run.py`: the 44 agent runs.
- `blind.py`, `judge.py`: blind disclosure labels (author + gpt-4.1 as a second rater).
- `data/`: every run with all actions and results (`runs.jsonl`), mechanism output, both label sets and the blind key.

## Rerun

```bash
git clone https://github.com/browser-use/browser-use.git repo && cd repo
git fetch origin pull/6106/head:pr6106
git worktree add ../base ccd22fef47 && git worktree add ../pr pr6106 && cd ..
for b in base pr; do (cd $b && uv venv -p 3.12 .venv && VIRTUAL_ENV=$PWD/.venv uv pip install -e . python-dotenv); done
# copy this folder's files next to base/ and pr/, then:
mkdir -p data
base/.venv/bin/python mechanism.py data/mechanism_base.json
pr/.venv/bin/python mechanism.py data/mechanism_pr.json
OPENAI_API_KEY=... python run.py          # 44 runs, about $1 with gpt-4.1-mini
python blind.py export                     # then label data/blind_items.json by hand
OPENAI_API_KEY=... python judge.py && python blind.py join
```
