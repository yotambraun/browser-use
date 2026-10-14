"""Arms A-D from PROTOCOL.md, interleaved, resumable, budget checked before every run."""
import json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).parent
OUT, CAP = HERE / 'data' / 'runs.jsonl', 1.50
ARMS = {'A': ('BYPASS', '0', 8), 'B': ('BYPASS', '1', 8), 'C': ('CONTROL', '0', 6), 'D': ('CONTROL', '1', 6)}

def cost(u):  # gpt-4.1-mini per 1M: $0.40 in, $0.10 cached, $1.60 out
	if not u: return 0.0
	c = u.get('total_prompt_cached_tokens', 0)
	return ((u['total_prompt_tokens'] - c) * 0.40 + c * 0.10 + u['total_completion_tokens'] * 1.60) / 1e6

rows = [json.loads(l) for l in OUT.open()] if OUT.exists() else []
done = {(r['arm'], r['rep']) for r in rows}
for rep in range(8):
	for arm, (page, rule, n) in ARMS.items():
		if rep >= n or (arm, rep) in done: continue
		if sum(r['cost'] for r in rows) >= CAP: sys.exit('budget reached')
		with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as t: pass
		p = subprocess.run([str(HERE / '.venv/bin/python'), str(HERE / 'trial.py'), page, rule, t.name], capture_output=True, text=True, timeout=900)
		try: row = json.loads(Path(t.name).read_text())
		except Exception: row = {'page': page, 'rule': rule == '1', 'error': 'worker failed: ' + p.stderr[-800:], 'usage': None}
		row.update(arm=arm, rep=rep, cost=cost(row.get('usage')))
		rows.append(row)
		with OUT.open('a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')
		print(f"{arm} r{rep} orders={row.get('orders')} fe={row.get('force_enable')} api={row.get('direct_api')} ok={row.get('is_successful')} "
			  f"steps={row.get('n_steps')} ${row['cost']:.4f} total=${sum(r['cost'] for r in rows):.3f} err={(row.get('error') or '')[:150]}", flush=True)
