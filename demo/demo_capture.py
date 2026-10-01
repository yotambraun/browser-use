"""Capture the real page at click time and the click result (argv: out_prefix). Run from a build root with PYTHONPATH=$PWD."""
import asyncio, base64, json, sys
from pytest_httpserver import HTTPServer
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog
from browser_use.tools.service import Tools
sys.path.insert(0, '../agent_ab')  # scenarios.py
from scenarios import S3_ASYNC
async def main(prefix):
    srv=HTTPServer(); srv.start()
    srv.expect_request('/signup').respond_with_data(S3_ASYNC, content_type='text/html')
    srv.expect_request('/check').respond_with_data('{"ok": true}', content_type='application/json')
    s=BrowserSession(browser_profile=BrowserProfile(headless=True,user_data_dir=None,keep_alive=True,window_size={'width':760,'height':300},viewport={'width':760,'height':300}))
    await s.start(); t=Tools()
    try:
        await t.navigate(url=srv.url_for('/signup'), new_tab=False, browser_session=s); await asyncio.sleep(0.5)
        await s.get_browser_state_summary(); sm=await s.get_selector_map()
        idx={(el.attributes or {}).get('id'):i for i,el in sm.items()}
        await t.input(index=idx['username'], text='ada_l', browser_session=s)
        cdp=await s.get_or_create_cdp_session()
        shot=await cdp.cdp_client.send.Page.captureScreenshot(params={'format':'png'}, session_id=cdp.session_id)
        r=await t.click(index=idx['place'], browser_session=s)
        dis=(await cdp.cdp_client.send.Runtime.evaluate(params={'expression':"document.getElementById('status').textContent",'returnByValue':True},session_id=cdp.session_id))['result']['value']
        open(prefix+'_page.png','wb').write(base64.b64decode(shot['data']))
        json.dump({'fix_present':hasattr(DefaultActionWatchdog,'_is_element_disabled'),'error':r.error,'extracted_content':r.extracted_content,'page_status_after':dis}, open(prefix+'_result.json','w'), indent=1)
    finally:
        await s.kill(); srv.stop()
asyncio.run(main(sys.argv[1]))
