# Evidence: browser-use#6106 against the #6068 bypass

Pre-registered test of [browser-use#6106](https://github.com/browser-use/browser-use/pull/6106) (head `71da6df`)
against its merge base on main (`ccd22fe`), using the repro from
[browser-use#6068](https://github.com/browser-use/browser-use/issues/6068).

- `PROTOCOL.md`: the plan, predictions and decision rules, committed before any measurement.
- `RUBRIC.md`: how final messages are labeled for disclosure, blind to the build.
- `pages.py`: the three local pages (bypass, legitimate with a 1.5 s delay, legitimate with no delay) and the CSP pages.
- `mechanism.py`: deterministic check of the `evaluate` action, no LLM.
- `trial.py`, `run.py`: the 44 agent runs.
- `blind.py`, `judge.py`: blind disclosure labels (author + gpt-4.1 as a second rater).

Results and data are added in later commits.
