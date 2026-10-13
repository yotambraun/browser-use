"""MAIN vs FIX on BU-02h, interleaved, resumable, budget checked before each run. See PROTOCOL.md."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent
S = Path(os.environ.get('BU_WORKDIR', '.'))  # holds bu-main/, bu-rebase/ (each with .venv) and adam6031/patched/
PACK = S / 'adam6031' / 'patched'
BUILDS = {'MAIN': S / 'bu-main', 'FIX': S / 'bu-rebase'}
N, CAP = 6, 0.60
OUT = HERE / 'data' / 'runs.jsonl'


def cost(u):  # gpt-4.1-mini: $0.40 in, $0.10 cached, $1.60 out per 1M
	if not u: return 0.0
	c = u.get('total_prompt_cached_tokens', 0)
	return ((u['total_prompt_tokens'] - c) * 0.40 + c * 0.10 + u['total_completion_tokens'] * 1.60) / 1e6


task = next(c for c in json.loads((PACK / 'expected_answers.json').read_text())['cases'] if c['id'] == 'BU-02h')['task']
rows = [json.loads(l) for l in OUT.open()] if OUT.exists() else []
done = {(r['build'], r['rep']) for r in rows}
for rep in range(N):
	for build in ('MAIN', 'FIX'):
		if (build, rep) in done: continue
		spent = sum(r['cost'] for r in rows)
		if spent >= CAP: sys.exit(f'budget reached at ${spent:.3f}')
		with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as t: pass
		py = BUILDS[build] / '.venv' / 'bin' / 'python'
		p = subprocess.run([str(py), str(HERE / 'agent_once.py'), str(BUILDS[build]), t.name, str(PACK)],
						   env={**os.environ, 'BU02H_TASK': task}, capture_output=True, text=True, timeout=900)
		try:
			row = json.loads(Path(t.name).read_text())
		except Exception:
			row = {'error': 'worker failed: ' + p.stderr[-800:], 'usage': None, 'fix_present': None}
		row.update(build=build, rep=rep, cost=cost(row.get('usage')))
		assert row.get('fix_present') in (None, build == 'FIX'), 'build mismatch'
		rows.append(row)
		with OUT.open('a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')
		print(f"{build:4} r{rep} orders={row.get('orders_posted')} bypass={row.get('bypass')} ok={row.get('is_successful')} "
			  f"steps={row.get('n_steps')} rep={row.get('identical_repeats')} dis_err={row.get('disabled_errors')} "
			  f"${row['cost']:.4f} total=${sum(r['cost'] for r in rows):.3f} err={row.get('error')}", flush=True)
