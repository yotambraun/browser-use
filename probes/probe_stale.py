"""Is the element node's `disabled` attribute stale at click time when the page enables the button after the snapshot?"""
import asyncio, json
from pytest_httpserver import HTTPServer
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.tools.service import Tools
PAGE = """<html><body><input id="name"><button id="go" disabled>Place order</button><script>
const b=document.getElementById('go'); b.addEventListener('click',()=>window.clicked=1);
document.getElementById('name').addEventListener('input',e=>{b.disabled=!e.target.value});</script></body></html>"""
async def main():
    srv=HTTPServer(); srv.start(); srv.expect_request('/f').respond_with_data(PAGE, content_type='text/html')
    s=BrowserSession(browser_profile=BrowserProfile(headless=True,user_data_dir=None,keep_alive=True)); await s.start(); t=Tools()
    try:
        await t.navigate(url=f'http://{srv.host}:{srv.port}/f', new_tab=False, browser_session=s); await asyncio.sleep(0.4)
        await s.get_browser_state_summary(); sm=await s.get_selector_map()
        idx={(el.attributes or {}).get('id'):i for i,el in sm.items()}
        print('indexes from one snapshot:', idx)
        r1=await t.input(index=idx['name'], text='Ada', browser_session=s)   # enables the button live
        node=await s.get_element_by_index(idx['go'])
        cdp=await s.get_or_create_cdp_session()
        live=(await cdp.cdp_client.send.Runtime.evaluate(params={'expression':"document.getElementById('go').disabled",'returnByValue':True},session_id=cdp.session_id))['result']['value']
        print(json.dumps({'snapshot_node_attrs': node.attributes, 'live_disabled_after_input': live}))
        r2=await t.click(index=idx['go'], browser_session=s)
        ran=(await cdp.cdp_client.send.Runtime.evaluate(params={'expression':'window.clicked||0','returnByValue':True},session_id=cdp.session_id))['result']['value']
        print(json.dumps({'click_error': r2.error, 'click_reported': r2.extracted_content, 'handler_ran': bool(ran)}))
    finally:
        await s.kill(); srv.stop()
asyncio.run(main())
