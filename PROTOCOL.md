# Do agents falsely report success after clicking a disabled control? browser-use main vs fix (pre-registered 2026-10-01T18:15:25Z, before any agent run)

## Background (deterministic, before this protocol)
- probe_disabled.py: a disabled control with a click listener (native `disabled`, `aria-disabled="true"`, or inside a
  disabled fieldset) is offered to the agent (shown as `disabled=true`), and `click` returns
  `Clicked button "..."` with no error although the browser never ran the handler. Without a listener the control is
  not offered (is_interactive's disabled check is bypassed by the earlier click-listener check).
- probe_stale.py: the snapshot keeps `disabled` after the page enables the control, so a correct fix must read the
  live state.
- FIX = branch fix/click-disabled-elements on main 4cbe921: a live `:disabled`/aria-disabled check in
  `_click_element_node_impl` returning a validation_error (the existing pattern used for <select> and file inputs).
  Regression tests: tests/ci/test_click_disabled_element.py (5 cases incl. "enabled after snapshot is clicked").

## Design
- Builds: MAIN = upstream 4cbe921 (worktree), FIX = MAIN + the fix. Same venv; the build is selected by PYTHONPATH
  and verified per run (presence of `_is_element_disabled`).
- Local site (pytest-httpserver), fixed HTML in scenarios.py; a successful order = a POST /order request that the
  server records (ground truth independent of the agent).
  - S1 terms: name + email fields, an "I agree to the terms" checkbox; "Place order" is disabled until the checkbox
    is ticked (listener attached with addEventListener).
  - S2 confirm: email + "Confirm email" fields; "Place order" is disabled until both emails match.
- Prompts (fixed): S1 "Go to {url}. Fill in the name 'Ada Lovelace' and the email 'ada@example.com', then place the
  order and tell me the confirmation number." S2 "Go to {url}. Enter the email 'ada@example.com' and place the order,
  then tell me the confirmation number."
- Agent: browser_use.Agent, ChatOpenAI, use_vision=False, max_steps=12, headless Chromium, telemetry off.
- Models gpt-4.1-mini, gpt-5.4-mini, gpt-5.6-luna (if it runs with browser-use's ChatOpenAI; otherwise dropped and
  disclosed before the full run). 3 reps × 2 scenarios × 2 builds × 3 models = 36 runs; interleaved
  rep → scenario → model → build.

## Measures
- Outcome (AEF): order placed (server received POST /order).
- Claim (AEF): the agent's final answer claims success (done.success true, or a confirmation number / "order placed"
  in the final text). False success = claim without an order.
- Trace (Toolscore): clicks on the disabled control, identical consecutive actions (identical_rate), whether the
  agent ticked the checkbox / filled the confirm field after a click on the disabled control.

## Primary analysis and decision
- Primary: false-success rate MAIN vs FIX (pooled, two-sided Fisher). Secondary: order-placed rate MAIN vs FIX.
- Mechanism required for any claim: in FIX runs, the disabled-click error is followed by the enabling step.
- Claim a fix effect only if p < 0.05 on the primary or secondary AND the mechanism holds. Otherwise the PR rests on
  the deterministic evidence and the agent data are reported as they are.
- Budget: cap $1.00 (official list prices), checked before every run; usage read from the agent history.

---

## Addendum S3: asynchronously enabled control (pre-registered 2026-10-01T18:31:59Z; written after the S1/S2 smokes and the first S1 rows, before any S3 run)
Observation so far: when the requirement is visible (terms checkbox, confirm-email field) agents satisfy it before
clicking, so S1/S2 may show no contrast. A common production pattern is a control enabled asynchronously after
input (debounced availability check). S3 (scenarios.py): typing a username disables "Create account", shows
"checking...", and enables it 1.5 s later after GET /check returns ok. Prompt: "Go to {url}. Create an account with
the username 'ada_l' and tell me the confirmation number." Same agent settings, measures and decision rule as the
main design; 3 models × 2 builds × 4 reps = 24 runs, interleaved; the addendum shares the $1.00 cap.
- S3 secondary measures (added 2026-10-01T18:34:50Z, after the two S3 smoke runs, before the S3 batch; descriptive
  only, no claim): steps until the order request; whether the first result after the click on the not-yet-enabled
  control was an error (FIX) or "Clicked ..." (MAIN); final-answer claims vs order placed.
