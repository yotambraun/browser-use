# Evidence: the browser-use agent enables a disabled button with `evaluate` and often reports a plain success

Supporting data for a browser-use issue, which follows browser-use#6031 (BU-02h, found by @Adam13y).

- `repro.py`: the standalone script from the issue (browser-use 0.13.11 from PyPI, gpt-4.1-mini).
- `PROTOCOL.md`: written before any run. `RESULTS.md`: results, decision rules, and notes added after the data.
- `trial.py` / `run.py`: one run per subprocess, arms A–D, resumable, with a budget cap.
- `data/runs.jsonl`: every run (actions, results, final message, usage). `data/disclosure_labels.json`: hand labels
  for the final messages. `data/repro_check_1.txt`: the first run of `repro.py`.

Related runs on Adam's fixture (main vs #5965):
https://github.com/yotambraun/browser-use/tree/evidence/click-disabled/agent_ab/bu02h
