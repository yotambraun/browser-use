"""Blind labeling helper. `python blind.py export` | `python blind.py join` (see RUBRIC.md)."""
import json, random, sys, uuid
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'
runs = [json.loads(l) for l in (DATA / 'runs.jsonl').read_text().splitlines()]
run_id = lambda r: f"{r['build']}|{r['page']}|{r['rep']}"

if sys.argv[1] == 'export':
	todo = [r for r in runs if r['page'] == '/bypass' and (r.get('orders') or 0) > 0]
	random.Random(uuid.uuid4().int).shuffle(todo)
	key, items = {}, []
	for r in todo:
		bid = uuid.uuid4().hex[:6]
		key[bid] = run_id(r)
		items.append({'id': bid, 'final_message': r['final'], 'label_A': None})
	(DATA / 'blind_key.json').write_text(json.dumps(key, indent=1))
	(DATA / 'blind_items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False))
	print(f'{len(items)} messages exported')
elif sys.argv[1] == 'join':
	key = json.loads((DATA / 'blind_key.json').read_text())
	items = {i['id']: i for i in json.loads((DATA / 'blind_items.json').read_text())}
	b = json.loads((DATA / 'labels_B.json').read_text())
	out = {key[i]: {'label_A': items[i]['label_A'], 'label_B': b[i]['label'], 'B_reason': b[i]['reason']} for i in key}
	(DATA / 'disclosure_labels.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
	agree = sum(v['label_A'] == v['label_B'] for v in out.values())
	print(f'agreement A vs B: {agree}/{len(out)}')
	for k, v in out.items():
		if v['label_A'] != v['label_B']:
			print('DISAGREE', k, v)
