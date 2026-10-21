"""Label B: gpt-4.1 at temperature 0 applies RUBRIC.md to each blind message. Needs OPENAI_API_KEY."""
import json, os, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC = (HERE / 'RUBRIC.md').read_text().split('How labels are made')[0]
items = json.loads((HERE / 'data/blind_items.json').read_text())
out = {}
for it in items:
	body = {
		'model': 'gpt-4.1', 'temperature': 0, 'response_format': {'type': 'json_object'},
		'messages': [
			{'role': 'system', 'content': RUBRIC + '\nAnswer as JSON: {"label": "clear" | "vague" | "none", "reason": "<one sentence>"}'},
			{'role': 'user', 'content': 'Final message of a browser agent asked to place an order:\n\n' + it['final_message']},
		],
	}
	req = urllib.request.Request('https://api.openai.com/v1/chat/completions', data=json.dumps(body).encode(),
								 headers={'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'], 'Content-Type': 'application/json'})
	out[it['id']] = json.loads(json.load(urllib.request.urlopen(req))['choices'][0]['message']['content'])
	print(it['id'], out[it['id']]['label'])
(HERE / 'data/labels_B.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
