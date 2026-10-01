"""Deterministic claim-vs-reality probes for browser-use actions (no LLM).

For each scenario: load a local page, run one action exactly as the agent would, then read the real page state via
CDP. A finding = the ActionResult reports success (no error) while the page state shows the action did not happen.

    .venv/bin/python ../probe_actions.py      # from src/, writes ../data/probe_results.json
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pytest_httpserver import HTTPServer

from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.tools.service import Tools

PAGES = {
	'/overlay': """<html><body>
		<button id="buy" onclick="window.clicked='buy'">Buy now</button>
		<div id="banner" style="position:fixed;inset:0;background:rgba(0,0,0,.5)" onclick="window.clicked='banner'">
		  <div style="background:#fff;margin:40px;padding:20px">We use cookies <button id="ok">Accept</button></div></div>
		</body></html>""",
	'/disabled_button': """<html><body>
		<button id="b" disabled onclick="window.clicked='b'">Submit order</button></body></html>""",
	'/readonly': """<html><body><input id="f" value="locked" readonly></body></html>""",
	'/disabled_input': """<html><body><input id="f" value="" disabled><input id="other"></body></html>""",
	'/maxlength': """<html><body><input id="f" maxlength="5"></body></html>""",
	'/js_reformat': """<html><body><input id="f" oninput="this.value=this.value.replace(/[^0-9]/g,'')"></body></html>""",
	'/select_disabled_opt': """<html><body><select id="s"><option value="a">Standard</option>
		<option value="b" disabled>Express</option></select></body></html>""",
	'/select_reset': """<html><body><select id="s" onchange="this.value='a'"><option value="a">Standard</option>
		<option value="b">Express</option></select></body></html>""",
	'/short': """<html><body><p>Short page.</p></body></html>""",
	'/inner_scroll': """<html><body style="margin:0"><div id="box" style="height:200px;overflow:auto">
		""" + ''.join(f'<p>row {i}</p>' for i in range(100)) + """</div></body></html>""",
}


async def js(session: BrowserSession, expr: str):
	cdp = await session.get_or_create_cdp_session()
	r = await cdp.cdp_client.send.Runtime.evaluate(params={'expression': expr, 'returnByValue': True}, session_id=cdp.session_id)
	return r.get('result', {}).get('value')


async def index_of(session: BrowserSession, pred) -> int | None:
	await session.get_browser_state_summary()
	for idx, el in (await session.get_selector_map()).items():
		if pred(el):
			return idx
	return None


def by_id(i):
	return lambda el: (el.attributes or {}).get('id') == i


async def run_case(tools, session, base, case):
	name, path, action, pre = case['name'], case['path'], case['action'], case.get('pre')
	await tools.navigate(url=base + path, new_tab=False, browser_session=session)
	await asyncio.sleep(0.4)
	if pre:
		await js(session, pre)
	kwargs = dict(case.get('kwargs', {}))
	if 'target' in case:
		idx = await index_of(session, by_id(case['target']))
		if idx is None:
			return {'name': name, 'note': f"target #{case['target']} not in selector map (not offered to the agent)"}
		kwargs['index'] = idx
	try:
		res = await getattr(tools, action)(browser_session=session, **kwargs)
		claim = {'error': res.error, 'extracted_content': res.extracted_content, 'long_term_memory': res.long_term_memory}
	except Exception as e:  # an exception is surfaced to the agent as an error
		claim = {'error': f'{type(e).__name__}: {e}', 'extracted_content': None}
	reality = await js(session, case['check'])
	ok = bool(case['expect'](reality))
	silent = claim['error'] in (None, '') and not ok
	return {'name': name, 'action': action, 'kwargs': {k: v for k, v in kwargs.items() if k != 'index'},
			'claim': claim, 'reality': reality, 'action_really_happened': ok, 'SILENT_SUCCESS': silent}


CASES = [
	{'name': 'click covered by cookie overlay', 'path': '/overlay', 'action': 'click', 'target': 'buy',
	 'check': 'window.clicked || null', 'expect': lambda v: v == 'buy'},
	{'name': 'click disabled button', 'path': '/disabled_button', 'action': 'click', 'target': 'b',
	 'check': 'window.clicked || null', 'expect': lambda v: v == 'b'},
	{'name': 'input into readonly field', 'path': '/readonly', 'action': 'input', 'target': 'f',
	 'kwargs': {'text': 'hello'}, 'check': "document.getElementById('f').value", 'expect': lambda v: v == 'hello'},
	{'name': 'input into disabled field', 'path': '/disabled_input', 'action': 'input', 'target': 'f',
	 'kwargs': {'text': 'hello'}, 'check': "document.getElementById('f').value", 'expect': lambda v: v == 'hello'},
	{'name': 'input longer than maxlength', 'path': '/maxlength', 'action': 'input', 'target': 'f',
	 'kwargs': {'text': '1234567890'}, 'check': "document.getElementById('f').value", 'expect': lambda v: v == '1234567890'},
	{'name': 'input rewritten by page JS', 'path': '/js_reformat', 'action': 'input', 'target': 'f',
	 'kwargs': {'text': 'ab12cd'}, 'check': "document.getElementById('f').value", 'expect': lambda v: v == 'ab12cd'},
	{'name': 'select disabled option', 'path': '/select_disabled_opt', 'action': 'select_dropdown', 'target': 's',
	 'kwargs': {'text': 'Express'}, 'check': "document.getElementById('s').value", 'expect': lambda v: v == 'b'},
	{'name': 'select reset by onchange', 'path': '/select_reset', 'action': 'select_dropdown', 'target': 's',
	 'kwargs': {'text': 'Express'}, 'check': "document.getElementById('s').value", 'expect': lambda v: v == 'b'},
	{'name': 'scroll page that cannot scroll', 'path': '/short', 'action': 'scroll', 'kwargs': {'down': True, 'pages': 1},
	 'check': 'window.scrollY', 'expect': lambda v: (v or 0) > 0},
	{'name': 'go_back with no history', 'path': '/short', 'action': 'go_back', 'pre': None,
	 'check': 'location.pathname', 'expect': lambda v: v != '/short'},
]


async def main():
	server = HTTPServer(); server.start()
	for path, html in PAGES.items():
		server.expect_request(path).respond_with_data(html, content_type='text/html')
	base = f'http://{server.host}:{server.port}'
	session = BrowserSession(browser_profile=BrowserProfile(headless=True, user_data_dir=None, keep_alive=True))
	await session.start()
	tools = Tools()
	out = []
	try:
		for case in CASES:
			try:
				r = await run_case(tools, session, base, case)
			except Exception as e:
				r = {'name': case['name'], 'probe_error': f'{type(e).__name__}: {e}'}
			out.append(r)
			print(json.dumps(r, ensure_ascii=False, default=str)[:600], flush=True)
	finally:
		await session.kill(); server.stop()
	Path('../data').mkdir(exist_ok=True)
	Path('../data/probe_results.json').write_text(json.dumps(out, indent=1, default=str))


if __name__ == '__main__':
	asyncio.run(main())
