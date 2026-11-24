import csv,json
from pathlib import Path
p=Path(__file__).resolve().parents[1]
latest=json.loads((p/'reports/latest.json').read_text())
r=p/'reports/runs'/latest['run_id']
data={n:list(csv.DictReader((r/(n+'.csv')).open())) for n in ['APDetail','InventoryPosition','action_queue']}
(p/'scripts/erp_excel_data.json').write_text(json.dumps(data))
