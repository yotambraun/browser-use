import asyncio, json
from pytest_httpserver import HTTPServer
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.tools.service import Tools
VUE = """<html><body><div id="app"><button id="t" :disabled="true" @click="go">Place order</button></div>
<script src="https://unpkg.com/vue@3.5.13/dist/vue.global.prod.js"></script>
<script>Vue.createApp({methods:{go(){window.clicked=1}}}).mount('#app')</script></body></html>"""
REACT = """<html><body><div id="root"></div>
<script src="https://unpkg.com/react@18.3.1/umd/react.production.min.js"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js"></script>
<script>ReactDOM.createRoot(document.getElementById('root')).render(
 React.createElement('button',{id:'t',disabled:true,onClick:()=>{window.clicked=1}},'Place order'))</script></body></html>"""
async def main():
    srv=HTTPServer(); srv.start()
    for k,v in (("vue",VUE),("react",REACT)): srv.expect_request('/'+k).respond_with_data(v, content_type='text/html')
    s=BrowserSession(browser_profile=BrowserProfile(headless=True,user_data_dir=None,keep_alive=True)); await s.start(); t=Tools()
    try:
        for k in ("vue","react"):
            await t.navigate(url=srv.url_for('/'+k), new_tab=False, browser_session=s); await asyncio.sleep(2.0)
            cdp=await s.get_or_create_cdp_session()
            dis=(await cdp.cdp_client.send.Runtime.evaluate(params={'expression':"(document.getElementById('t')||{}).disabled",'returnByValue':True},session_id=cdp.session_id))['result'].get('value')
            await s.get_browser_state_summary()
            idx=next((i for i,el in (await s.get_selector_map()).items() if (el.attributes or {}).get('id')=='t'),None)
            row={'framework':k,'button_disabled_in_dom':dis,'offered_to_agent':idx is not None}
            if idx is not None:
                r=await t.click(index=idx, browser_session=s); row.update(click_error=r.error, click_reported=r.extracted_content)
            print(json.dumps(row))
    finally:
        await s.kill(); srv.stop()
asyncio.run(main())
