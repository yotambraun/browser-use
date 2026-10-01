"""One agent run (subprocess). argv: model scenario build_dir out_json. Prints nothing; writes one JSON object."""
import asyncio, json, os, re, sys, time
from pathlib import Path

model, scen, build_dir, out_path = sys.argv[1:5]
sys.path.insert(0, build_dir)  # the build under test (MAIN worktree or FIX tree) wins over the editable install
os.environ.update(ANONYMIZED_TELEMETRY='false', BROWSER_USE_LOGGING_LEVEL='error', BROWSER_USE_CLOUD_SYNC='false')
assert os.environ.get('OPENAI_API_KEY'), 'set OPENAI_API_KEY'

import browser_use
from browser_use import Agent, ChatOpenAI
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response
sys.path.insert(0, str(Path(__file__).parent))
from scenarios import SCENARIOS, CONFIRMATION

orders = []
def order_handler(request):
	orders.append(request.get_json(silent=True))
	return Response(json.dumps({'confirmation': CONFIRMATION}), content_type='application/json')

async def main():
	html, prompt = SCENARIOS[scen]
	srv = HTTPServer(); srv.start()
	srv.expect_request('/checkout').respond_with_data(html, content_type='text/html')
	srv.expect_request('/order', method='POST').respond_with_handler(order_handler)
	srv.expect_request('/check').respond_with_data(json.dumps({'ok': True}), content_type='application/json')
	url = srv.url_for('/checkout')
	session = BrowserSession(browser_profile=BrowserProfile(headless=True, user_data_dir=None, keep_alive=False))
	agent = Agent(task=prompt.format(url=url), llm=ChatOpenAI(model=model), browser_session=session, use_vision=False,
				  calculate_cost=True)
	t0 = time.time(); err = None
	try:
		hist = await agent.run(max_steps=12)
	except Exception as e:
		hist, err = None, f'{type(e).__name__}: {e}'
	finally:
		srv.stop()
	steps = []
	if hist:
		for h in hist.history:
			acts = [a.model_dump(exclude_none=True, mode='json') for a in (h.model_output.action if h.model_output else [])]
			res = [{'error': r.error, 'content': (r.extracted_content or '')[:300], 'is_done': r.is_done, 'success': r.success} for r in h.result]
			steps.append({'actions': acts, 'results': res})
	final = (hist.final_result() if hist else None) or ''
	u = hist.usage if hist else None
	row = {'model': model, 'scenario': scen, 'build_dir': build_dir, 'browser_use_file': browser_use.__file__,
		   'fix_present': hasattr(DefaultActionWatchdog, '_is_element_disabled'), 'error': err,
		   'order_placed': len(orders) > 0, 'orders': orders, 'final': final[:1500],
		   'done_success': hist.is_successful() if hist else None, 'is_done': hist.is_done() if hist else False,
		   'claims_success': bool(hist and hist.is_successful()) or (CONFIRMATION in final) or bool(re.search(r'order (has been |was )?(placed|confirmed)', final.lower())),
		   'steps': steps, 'n_steps': len(steps), 'seconds': round(time.time() - t0, 1),
		   'usage': u.model_dump() if u else None}
	Path(out_path).write_text(json.dumps(row, ensure_ascii=False))

asyncio.run(main())
