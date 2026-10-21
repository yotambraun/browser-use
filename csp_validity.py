"""After-data validity check for M9/M10: is the CSP header actually enforced on the test pages?"""
import asyncio, os, json
os.environ.update(ANONYMIZED_TELEMETRY='false', BROWSER_USE_LOGGING_LEVEL='error')
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.tools.service import Tools
from pages import serve
PROBE = "new Promise(r=>{const s=document.createElement('script');s.textContent='window.__inline_ran=1';document.head.appendChild(s);setTimeout(()=>r(String(window.__inline_ran===1)),100)})"
async def main():
	srv, base, _ = serve(); s = BrowserSession(browser_profile=BrowserProfile(headless=True, user_data_dir=None)); await s.start(); t = Tools(); out = {}
	for p in ['/csp-self', '/csp-inline', '/bypass']:
		await t.navigate(url=base + p, new_tab=False, browser_session=s); await asyncio.sleep(0.3)
		cdp = await s.get_or_create_cdp_session()
		r = await cdp.cdp_client.send.Runtime.evaluate(params={'expression': PROBE, 'awaitPromise': True, 'returnByValue': True}, session_id=cdp.session_id)
		out[p] = {'inline_script_ran': r['result'].get('value')}
	await s.kill(); srv.shutdown(); print(json.dumps(out))
asyncio.run(main())
