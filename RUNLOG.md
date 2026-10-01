| 2026-10-01T18:28:29Z | fix branch: 5 new tests pass; full tests/ci 1208 passed 35 skipped; smokes S1 (main+fix, 4.1-mini), S2 (main: 4.1-mini, luna) all placed orders without hitting the disabled button; full 36-run A/B started | running |
| 2026-10-01T18:30:13Z | full run attempt 1 INVALID: runner resolved the venv python symlink to the base interpreter -> 36 import failures, $0 spent; rows moved to data/ab_invalid_venv_path.jsonl; fixed (abspath), verified 'venv ok' | fixed |
| 2026-10-01T18:30:22Z | full 36-run A/B relaunched (smokes ≈$0.03 not counted in the cap) | running |
| 2026-10-01T18:32:22Z | mid-batch, additive worker change: GET /check route + S3 page (S1/S2 never request /check; no effect on them). Addendum S3 pre-registered | note |
| 2026-10-01T18:39:23Z | main A/B done: S1/S2 36/36 orders in both builds, 0 disabled clicks, $0.180. S3 batch (24) started | running |
| 2026-10-01T19:03:24Z | S3 done ($0.42 total). Scope fixed to :disabled; red-on-main verified properly; full CI 1208 passed; Vue/React verified; committed 22c4e78; drafts in posting/ | done |
