"""Pre-registered A/B (PROTOCOL.md): MAIN vs FIX, resumable, budget checked before every run.

    python run_ab.py [--cells S1,S2] [--reps 3] [--out data/ab_runs.jsonl] [--cap 1.0]
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent
BUILDS = {'MAIN': (HERE.parent / 'wt-main').resolve(), 'FIX': (HERE.parent / 'src').resolve()}
MODELS = ['gpt-4.1-mini', 'gpt-5.4-mini', 'gpt-5.6-luna']
PRICES = {'gpt-4.1-mini': (0.40, 0.10, 1.60), 'gpt-5.4-mini': (0.75, 0.075, 4.50), 'gpt-5.6-luna': (0.20, 0.02, 1.20)}
PY = os.path.abspath(HERE.parent / 'src' / '.venv' / 'bin' / 'python')  # not resolve(): the venv python is a symlink


def cost(model, u):
	if not u: return 0.0
	pin, pcached, pout = PRICES[model]
	cached = u.get('total_prompt_cached_tokens', 0)
	return ((u['total_prompt_tokens'] - cached) * pin + cached * pcached + u['total_completion_tokens'] * pout) / 1e6


def spent():
	return sum(json.loads(l)['our_cost_usd'] for p in (HERE / 'data').glob('*runs*.jsonl') if 'invalid' not in p.name for l in p.open())


def main():
	a = argparse.ArgumentParser()
	a.add_argument('--cells', default='S1,S2'); a.add_argument('--reps', type=int, default=3)
	a.add_argument('--out', default='data/ab_runs.jsonl'); a.add_argument('--cap', type=float, default=1.0)
	args = a.parse_args()
	out = HERE / args.out
	done = {(r['model'], r['scenario'], r['build'], r['rep']) for r in map(json.loads, out.open())} if out.exists() else set()
	for rep in range(args.reps):
		for scen in args.cells.split(','):
			for model in MODELS:
				for build in ('MAIN', 'FIX'):
					if (model, scen, build, rep) in done: continue
					if spent() >= args.cap: print('budget reached; stopping', flush=True); return
					with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp: pass
					p = subprocess.run([PY, str(HERE / 'agent_once.py'), model, scen, str(BUILDS[build]), tmp.name],
									   capture_output=True, text=True, timeout=900)
					try:
						row = json.loads(Path(tmp.name).read_text())
					except Exception:
						row = {'model': model, 'scenario': scen, 'error': 'worker failed: ' + p.stderr[-500:], 'usage': None,
							   'order_placed': False, 'claims_success': False, 'steps': [], 'fix_present': None}
					row.update(build=build, rep=rep, our_cost_usd=cost(model, row.get('usage')))
					assert row.get('fix_present') in (None, build == 'FIX'), 'build mismatch'
					with out.open('a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')
					dis = sum(1 for s in row['steps'] for r in s['results'] if r['error'] and 'disabled' in r['error'])
					print(f"{model:13} {scen} {build:4} r{rep} order={row['order_placed']} claims={row['claims_success']} "
						  f"steps={len(row['steps'])} disabled_errors={dis} ${row['our_cost_usd']:.4f} total=${spent():.3f} err={row.get('error')}", flush=True)


if __name__ == '__main__':
	main()
