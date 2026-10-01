import asyncio

from pytest_httpserver import HTTPServer

from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.tools.service import Tools

PAGE = """<html><body>
<button id="place" disabled>Place order</button>
<script>
  document.getElementById('place').addEventListener('click', () => { window.ordered = true })
</script>
</body></html>"""


async def main():
	server = HTTPServer()
	server.start()
	server.expect_request('/').respond_with_data(PAGE, content_type='text/html')
	session = BrowserSession(browser_profile=BrowserProfile(headless=True, user_data_dir=None))
	await session.start()
	tools = Tools()
	await tools.navigate(url=server.url_for('/'), new_tab=False, browser_session=session)
	await session.get_browser_state_summary()
	index = next(i for i, el in (await session.get_selector_map()).items() if el.attributes.get('id') == 'place')

	result = await tools.click(index=index, browser_session=session)
	cdp = await session.get_or_create_cdp_session()
	ordered = await cdp.cdp_client.send.Runtime.evaluate(
		params={'expression': 'window.ordered === true', 'returnByValue': True}, session_id=cdp.session_id
	)
	print('error:            ', result.error)
	print('extracted_content:', result.extracted_content)
	print('handler ran:      ', ordered['result']['value'])
	await session.kill()
	server.stop()


asyncio.run(main())
