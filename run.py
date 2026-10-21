"""Runs the 44 pre-registered agent runs in a fixed shuffled order (seed 6106). Resumable; stops at the cost cap.
Usage: python run.py   (needs OPENAI_API_KEY in the environment)"""
import json, random, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDS = {'BASE': HERE / 'base/.venv/bin/python', 'PR': HERE / 'pr/.venv/bin/python'}
N = {'/bypass': 10, '/async': 6, '/sync': 6}
CAP = 2.00
DATA = HERE / 'data'; DATA.mkdir(exist_ok=True)
OUT = DATA / 'runs.jsonl'

plan = [(b, p, i) for b in BUILDS for p, n in N.items() for i in range(n)]
random.Random(6106).shuffle(plan)
done = {(r['build'], r['page'], r['rep']) for r in map(json.loads, OUT.read_text().splitlines())} if OUT.exists() else set()
spent = sum((json.loads(l).get('cost') or 0) for l in OUT.read_text().splitlines()) if OUT.exists() else 0.0

for k, (build, page, rep) in enumerate(plan, 1):
	if (build, page, rep) in done:
		continue
	if spent >= CAP:
		print(f'cost cap reached (${spent:.3f}); stopping'); break
	tmp = DATA / 'tmp.json'
	tmp.unlink(missing_ok=True)
	p = subprocess.run([str(BUILDS[build]), str(HERE / 'trial.py'), page, str(tmp)], cwd=HERE, capture_output=True, text=True, timeout=900)
	row = json.loads(tmp.read_text()) if tmp.exists() else {'page': page, 'error': f'no output; exit {p.returncode}: {p.stderr[-800:]}', 'cost': 0}
	row.update(build=build, rep=rep, order_index=k)
	with OUT.open('a') as f:
		f.write(json.dumps(row, ensure_ascii=False) + '\n')
	spent += row.get('cost') or 0
	print(f"{k:2}/44 {build:4} {page:7} r{rep} orders={row.get('orders')} success={row.get('is_successful')} "
		  f"fe={row.get('force_enable')} api={row.get('direct_api')} warn={row.get('warning_shown')} "
		  f"err={bool(row.get('error'))} ${row.get('cost') or 0:.4f} total=${spent:.3f}", flush=True)
