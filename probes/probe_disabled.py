"""Which disabled controls are offered to the agent, what does the LLM see, and what does click report?

    cd src && .venv/bin/python ../probe_disabled.py      # writes ../data/probe_disabled.json
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pytest_httpserver import HTTPServer

from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.tools.service import Tools

VARIANTS = {
	'native_disabled_no_listener': '<button id="t" disabled>Submit order</button>',
	'native_disabled_onclick_attr': '<button id="t" disabled onclick="window.clicked=1">Submit order</button>',
	'native_disabled_addEventListener': '<button id="t" disabled>Submit order</button>'
	'<script>document.getElementById("t").addEventListener("click",()=>window.clicked=1)</script>',
	'aria_disabled_with_listener': '<div id="t" role="button" aria-disabled="true" tabindex="0">Submit order</div>'
	'<script>document.getElementById("t").addEventListener("click",()=>{if(this.getAttribute("aria-disabled")!=="true")window.clicked=1})</script>',
	'enabled_control': '<button id="t" onclick="window.clicked=1">Submit order</button>',
	'disabled_input_with_listener': '<input id="t" disabled value="x">'
	'<script>document.getElementById("t").addEventListener("click",()=>window.clicked=1)</script>',
}


async def main():
	server = HTTPServer(); server.start()
	for k, body in VARIANTS.items():
		server.expect_request(f'/{k}').respond_with_data(f'<html><body><p>Checkout</p>{body}</body></html>', content_type='text/html')
	base = f'http://{server.host}:{server.port}'
	s = BrowserSession(browser_profile=BrowserProfile(headless=True, user_data_dir=None, keep_alive=True))
	await s.start()
	tools, out = Tools(), []
	try:
		for k in VARIANTS:
			await tools.navigate(url=f'{base}/{k}', new_tab=False, browser_session=s)
			await asyncio.sleep(0.4)
			state = await s.get_browser_state_summary()
			llm_view = state.dom_state.llm_representation()
			idx = next((i for i, el in (await s.get_selector_map()).items() if (el.attributes or {}).get('id') == 't'), None)
			row = {'variant': k, 'offered_to_agent': idx is not None,
				   'llm_line': next((ln.strip() for ln in llm_view.splitlines() if 'Submit order' in ln or 'id=t' in ln or "value=x" in ln), None)}
			if idx is not None:
				res = await tools.click(index=idx, browser_session=s)
				cdp = await s.get_or_create_cdp_session()
				r = await cdp.cdp_client.send.Runtime.evaluate(params={'expression': 'window.clicked||0', 'returnByValue': True}, session_id=cdp.session_id)
				row.update({'click_error': res.error, 'click_reported': res.extracted_content,
							'handler_ran': bool(r['result'].get('value'))})
			out.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
	finally:
		await s.kill(); server.stop()
	Path('../data').mkdir(exist_ok=True)
	Path('../data/probe_disabled.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
	asyncio.run(main())
