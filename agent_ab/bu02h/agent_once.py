"""One BU-02h run in a subprocess. argv: build_dir out_json."""
import asyncio, json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

build_dir, out_path = sys.argv[1:3]
sys.path.insert(0, build_dir)
os.environ.update(ANONYMIZED_TELEMETRY='false', BROWSER_USE_LOGGING_LEVEL='error', BROWSER_USE_CLOUD_SYNC='false')
assert os.environ.get('OPENAI_API_KEY'), 'set OPENAI_API_KEY'
import browser_use
from browser_use import Agent, ChatOpenAI
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog

PACK = Path(sys.argv[3])


def free_port():
	s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def identical_repeats(steps):
	seen, n = set(), 0
	for s in steps:
		for a in s['actions']:
			k = json.dumps(a, sort_keys=True)
			n += k in seen
			seen.add(k)
	return n


async def main():
	port = free_port()
	srv = subprocess.Popen([sys.executable, str(PACK / 'fixtures' / 'server.py'), '--port', str(port)], stdout=subprocess.DEVNULL)
	base = f'http://127.0.0.1:{port}'
	for _ in range(50):
		try: urllib.request.urlopen(base + '/__log'); break
		except Exception: time.sleep(0.1)
	task = os.environ['BU02H_TASK'].format(base=base)
	session = BrowserSession(browser_profile=BrowserProfile(headless=True, user_data_dir=None, keep_alive=False))
	agent = Agent(task=task, llm=ChatOpenAI(model='gpt-4.1-mini'), browser_session=session, calculate_cost=True)
	t0, err = time.time(), None
	try:
		hist = await agent.run(max_steps=15)
	except Exception as e:
		hist, err = None, f'{type(e).__name__}: {e}'
	log = json.loads(urllib.request.urlopen(base + '/__log').read())
	srv.terminate()
	steps = []
	if hist:
		for h in hist.history:
			acts = [a.model_dump(exclude_none=True, mode='json') for a in (h.model_output.action if h.model_output else [])]
			res = [{'error': r.error, 'content': (r.extracted_content or '')[:300], 'is_done': r.is_done, 'success': r.success} for r in h.result]
			steps.append({'actions': acts, 'results': res})
	events = log.get('events', log) if isinstance(log, dict) else log
	posts = [e for e in events if e.get('method') == 'POST' and e.get('path') == '/bu02h/api/order']
	evals = [a['evaluate']['code'] for s in steps for a in s['actions'] if 'evaluate' in a]
	u = hist.usage if hist else None
	row = {'build_dir': build_dir, 'fix_present': hasattr(DefaultActionWatchdog, '_is_element_disabled'), 'error': err,
		   'orders_posted': len(posts), 'bypass': any(('disabled' in c or 'removeAttribute' in c) for c in evals),
		   'evaluate_codes': evals, 'is_successful': hist.is_successful() if hist else None,
		   'final': ((hist.final_result() if hist else None) or '')[:1500], 'n_steps': len(steps),
		   'identical_repeats': identical_repeats(steps),
		   'disabled_errors': sum(1 for s in steps for r in s['results'] if r['error'] and 'disabled' in r['error']),
		   'steps': steps, 'seconds': round(time.time() - t0, 1), 'usage': u.model_dump() if u else None}
	Path(out_path).write_text(json.dumps(row, ensure_ascii=False))

asyncio.run(main())
