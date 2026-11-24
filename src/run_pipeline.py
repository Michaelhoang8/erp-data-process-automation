"""Validate extracts, execute SQL, and publish an immutable local reporting run.
No external messages, ERP writes, or cloud flows are performed.
"""
import argparse,csv,datetime as dt,hashlib,html,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCHEMAS={
 'vendors':('Vendors','VendorID TEXT PRIMARY KEY,VendorName TEXT,PaymentTermsDays INTEGER'),
 'items':('Items','ItemID TEXT PRIMARY KEY,Description TEXT,UnitCostCents INTEGER,ReorderPoint INTEGER'),
 'invoices':('Invoices','InvoiceID TEXT PRIMARY KEY,VendorID TEXT,PostingDate TEXT,DueDate TEXT,AmountCents INTEGER'),
 'payments':('Payments','PaymentID TEXT PRIMARY KEY,InvoiceID TEXT,PaymentDate TEXT,AmountCents INTEGER'),
 'purchase_orders':('PurchaseOrders','OrderID TEXT PRIMARY KEY,VendorID TEXT,ItemID TEXT,OrderDate TEXT,PromisedDate TEXT,ReceivedDate TEXT,Quantity INTEGER'),
 'inventory_movements':('InventoryMovements','MovementID TEXT PRIMARY KEY,ItemID TEXT,Location TEXT,PostingDate TEXT,Quantity INTEGER,MovementType TEXT')}
NUMBERS={'PaymentTermsDays','UnitCostCents','ReorderPoint','AmountCents','Quantity'}
def export(path,headers,rows):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(headers);w.writerows(rows)
def run(raw,output,asof):
 dt.date.fromisoformat(asof)
 payload=b''.join((raw/(n+'.csv')).read_bytes() for n in SCHEMAS)
 code=(Path(__file__).read_bytes()+(ROOT/'sql/analysis.sql').read_bytes())
 runid=hashlib.sha256(payload+code+asof.encode()).hexdigest()[:20]
 target=output/'runs'/runid
 if (target/'manifest.json').exists():
  # Content fingerprint makes a repeated successful extraction a no-op.
  result=json.loads((target/'manifest.json').read_text());result['reused']=True;result['output_folder']=str(target.resolve())
  pointer=output/'latest.json';temp=output/'latest.tmp';temp.write_text(json.dumps(result,indent=2));temp.replace(pointer)
  (output/'dashboard.html').write_text((target/'dashboard.html').read_text(encoding='utf-8'),encoding='utf-8')
  return result
 target.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(':memory:')
 db.execute('CREATE TABLE Parameters(AsOf TEXT)');db.execute('INSERT INTO Parameters VALUES (?)',(asof,))
 errors=[];counts={};seen={};accepted={}
 for filename,(table,ddl) in SCHEMAS.items():
  db.execute(f'CREATE TABLE {table}({ddl})')
  headers=[r[1] for r in db.execute(f'PRAGMA table_info({table})')]
  seen[table]={};accepted[table]=set();counts[table]={'raw':0,'accepted':0,'rejected':0}
  with (raw/(filename+'.csv')).open(newline='',encoding='utf-8-sig') as f:
   reader=csv.DictReader(f)
   if reader.fieldnames!=headers:raise ValueError(f'{filename}: headers must be {headers}')
   for line,row in enumerate(reader,2):
    counts[table]['raw']+=1;reason=[];key=row[headers[0]];typed={}
    if key in seen[table]:
     if row!=seen[table][key]:raise ValueError(f'Conflicting duplicate {table} {key}; publication stopped')
     reason.append('Exact duplicate')
    seen[table][key]=row.copy()
    for field,value in row.items():
     try:
      if field=='ReceivedDate' and value=='':typed[field]=None
      elif value is None or value.strip()=='':raise ValueError('missing')
      elif field in NUMBERS:typed[field]=int(value)
      elif field.endswith('Date'):typed[field]=dt.date.fromisoformat(value).isoformat()
      else:typed[field]=value.strip()
     except (ValueError,AttributeError):reason.append('Invalid or missing '+str(field))
    if not reason:
     for field,parent in [('VendorID','Vendors'),('ItemID','Items'),('InvoiceID','Invoices')]:
      if field in typed and parent!=table and typed[field] not in accepted[parent]:reason.append('Unknown '+field)
     if table=='Invoices' and typed['DueDate']<typed['PostingDate']:reason.append('Due before posting')
     if table=='PurchaseOrders':
      if typed['PromisedDate']<typed['OrderDate']:reason.append('Promise before order')
      if typed['ReceivedDate'] and typed['ReceivedDate']<typed['OrderDate']:reason.append('Receipt before order')
     for field in ('AmountCents','UnitCostCents','ReorderPoint','PaymentTermsDays'):
      if field in typed and typed[field]<0:reason.append('Negative '+field)
     if table=='PurchaseOrders' and typed['Quantity']<=0:reason.append('Nonpositive order quantity')
     if table=='InventoryMovements':
      if typed['Location'] not in ('EDM','CAL','VAN'):reason.append('Unknown location')
      kind=typed['MovementType'];qty=typed['Quantity']
      if kind not in ('Opening','Receipt','Issue','Adjustment'):reason.append('Unknown movement type')
      elif (kind in ('Opening','Receipt') and qty<0) or (kind=='Issue' and qty>0):reason.append('Movement sign mismatch')
    if reason:
     errors.append((filename,line,key,'; '.join(reason),json.dumps(row)));counts[table]['rejected']+=1
    else:
     db.execute(f'INSERT INTO {table} VALUES ({",".join("?" for _ in headers)})',[typed[h] for h in headers]);accepted[table].add(key);counts[table]['accepted']+=1
 db.executescript((ROOT/'sql/analysis.sql').read_text())
 for name in ('APDetail','APAging','VendorPerformance','InventoryPosition','MonthlyInvoiceTrend'):
  cur=db.execute('SELECT * FROM '+name)
  export(target/(name+'.csv'),[c[0] for c in cur.description],cur.fetchall())
 export(target/'data_quality_exceptions.csv',['Source','Line','RecordID','Reason','RawRecord'],errors)
 def query(sql):
  cur=db.execute(sql);return [dict(zip([c[0] for c in cur.description],r)) for r in cur.fetchall()]
 ap=query('SELECT * FROM APDetail');stock=query('SELECT * FROM InventoryPosition');vendors=query('SELECT * FROM VendorPerformance');trend=query('SELECT * FROM MonthlyInvoiceTrend')
 total=sum(r['OpenCents'] for r in ap);overdue=sum(max(0,r['OpenCents']) for r in ap if r['DaysOverdue']>0)
 received=sum(r['ReceivedOrders'] for r in vendors);ontime=sum(r['OnTimeOrders'] for r in vendors)
 negative=[r for r in stock if r['OnHand']<0]
 checks={'source_row_accounting':all(c['raw']==c['accepted']+c['rejected'] for c in counts.values()),
 'ap_reconciliation':sum(r['AmountCents'] for r in ap)-sum(r['PaidCents'] for r in ap)==total,
 'aging_reconciliation':sum(r['OpenCents'] for r in query('SELECT * FROM APAging'))==total,
 'inventory_reconciliation':sum(r['OnHand'] for r in stock)==db.execute('SELECT COALESCE(SUM(Quantity),0) FROM InventoryMovements WHERE PostingDate<=?',(asof,)).fetchone()[0],
 'monthly_invoice_reconciliation':sum(r['InvoicedCents'] for r in trend)==sum(r['AmountCents'] for r in ap),
 'delivery_numerator_bounded':all(0<=r['OnTimeOrders']<=r['ReceivedOrders']<=r['Orders'] for r in vendors)}
 if not all(checks.values()):raise AssertionError(checks)
 tasks=[]
 for e in errors:tasks.append(('Data quality',e[2],e[3],'Data steward','Inspect source record; correct and re-extract'))
 for s in negative:tasks.append(('Inventory',s['ItemID']+'/'+s['Location'],f"Negative on-hand: {s['OnHand']}",'Warehouse manager','Reconcile count and movement history before replenishment'))
 for r in ap:
  if r['OpenCents']>0 and r['DaysOverdue']>90:tasks.append(('Accounts payable',r['InvoiceID'],f"{r['DaysOverdue']} days overdue",'AP analyst','Review approval and payment status; do not auto-pay'))
  if r['OpenCents']<0:tasks.append(('Accounts payable',r['InvoiceID'],'Overpayment / credit','AP analyst','Reconcile payment application'))
 export(target/'action_queue.csv',['Area','RecordID','Finding','OwnerRole','NextAction'],tasks)
 money=lambda cents:f'${cents/100:,.2f}'
 pct='N/A' if not received else f'{ontime/received:.1%}'
 def htmltable(rows,fields):
  return '<table><thead><tr>'+''.join('<th>'+html.escape(label)+'</th>' for key,label in fields)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(row[key]))+'</td>' for key,label in fields)+'</tr>' for row in rows)+'</tbody></table>'
 aging=[{'Bucket':r['AgingBucket'],'Invoices':r['InvoiceCount'],'Balance':money(r['OpenCents'])} for r in query('SELECT * FROM APAging ORDER BY CASE AgingBucket WHEN \'Current\' THEN 0 WHEN \'1-30 days\' THEN 1 WHEN \'31-60 days\' THEN 2 WHEN \'61-90 days\' THEN 3 WHEN \'90+ days\' THEN 4 ELSE 5 END')]
 vendorrows=[dict(r,Rate='N/A' if not r['ReceivedOrders'] else f"{r['OnTimeOrders']/r['ReceivedOrders']:.1%}") for r in vendors]
 body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ERP Operations Review</title><style>body{{margin:0;background:#f0f3f7;color:#183048;font:15px system-ui}}header{{background:#183048;color:white;padding:32px 5%}}main{{max-width:1200px;margin:auto;padding:24px}}h1{{font-size:32px}}h2{{font-size:21px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card,section{{background:white;border:1px solid #dce3ea;border-radius:10px;padding:22px;margin-bottom:20px}}strong{{display:block;font-size:27px;margin-top:12px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #e4e9ef}}p{{line-height:1.6}}section{{overflow:auto}}small{{color:#506579}}@media(max-width:760px){{.cards{{grid-template-columns:1fr 1fr}}main{{padding:12px}}}}</style><header>SYNTHETIC PORTFOLIO PROJECT · NORTHSTAR DISTRIBUTION<h1>ERP Data Analysis & Process Automation</h1>As of {asof} · CAD · Local reporting workflow</header><main><div class="cards"><div class="card">Open payable balance<strong>{money(total)}</strong></div><div class="card">Overdue payables<strong>{money(overdue)}</strong></div><div class="card">Received on time<strong>{pct}</strong></div><div class="card">Source exceptions<strong>{len(errors)}</strong></div></div><section><h2>Accounts payable aging</h2><p>Due today is current. Positive unpaid balances are liabilities; credits remain separate. This review does not initiate payments.</p>{htmltable(aging,[('Bucket','Aging bucket'),('Invoices','Invoices'),('Balance','Open CAD')])}</section><section><h2>Supplier delivery performance</h2><p>Rate includes received orders only. Open overdue orders are shown separately to avoid hiding unreceived commitments.</p>{htmltable(vendorrows,[('VendorName','Supplier'),('Orders','Orders'),('ReceivedOrders','Received'),('Rate','On-time rate'),('OpenOverdueOrders','Open overdue')])}</section><section><h2>Inventory exceptions</h2><p>{len(negative)} item/location balances are negative. Investigate movement records and physical counts; negative stock is retained for reconciliation.</p>{htmltable([r for r in stock if r['Status']!='Within policy'],[('ItemID','Item'),('Location','Location'),('OnHand','On hand'),('ReorderPoint','Reorder point'),('Status','Finding')])}</section><section><h2>Monthly invoice intake</h2>{htmltable([dict(r,Value=money(r['InvoicedCents'])) for r in trend],[('Month','Month'),('InvoiceCount','Invoices'),('Value','Invoiced CAD')])}</section><section><h2>Process priorities</h2><p>Resolve source exceptions, review invoices over 90 days overdue, and investigate negative inventory before making purchasing decisions. Use action_queue.csv for the full review list. Business Central and Power Automate connections have not been deployed.</p></section><small>Run {runid} · Deterministic generated data · No measured savings or real supplier performance claimed.</small></main></html>'''
 (target/'dashboard.html').write_text(body,encoding='utf-8')
 (target/'management_brief.md').write_text(f'''# ERP operational review — {asof}

Synthetic portfolio findings, in CAD.

- Open AP: {money(total)}; overdue positive balances: {money(overdue)}.
- On-time receipt rate: {pct}, based on {ontime} on-time / {received} received orders. Open overdue orders: {sum(r['OpenOverdueOrders'] for r in vendors)}.
- Negative stock positions: {len(negative)}; source records quarantined: {len(errors)}.

## Recommendations
1. AP analyst: prioritize unpaid invoices over 90 days past due, verify approvals and resolve disputes before payment. The report does not establish why invoices are unpaid.
2. Procurement: review Example Supplier 03's promised versus received dates and outstanding commitments. Its simulated delays are an intentional scenario assumption, not evidence about a real supplier.
3. Warehouse manager: investigate negative balances using movements and physical counts. Do not use negative stock as a reliable valuation without reconciliation.
4. Data steward: resolve quarantined rows in the source and re-extract. Keep the exception log and compare the new run to the prior run.

## Process improvement proposal
Replace repeated manual imports with a consistent extraction, schema validation, SQL analysis and review queue. Measure baseline minutes per run, rerun effort and exception closure time before estimating savings. No time savings or implementation in a Microsoft tenant have been measured.
''',encoding='utf-8')
 db.commit();backup=sqlite3.connect(target/'erp_analysis.sqlite');db.backup(backup);backup.close();db.close()
 result={'run_id':runid,'as_of':asof,'status':'needs_review' if errors or negative else 'completed','source':'synthetic ERP-style extracts','output_folder':str(target.resolve()),'source_counts':counts,'quality_exception_count':len(errors),'negative_stock_positions':len(negative),'checks':checks,'reused':False}
 (target/'manifest.json').write_text(json.dumps(result,indent=2))
 temp=output/'latest.tmp';temp.write_text(json.dumps(result,indent=2));temp.replace(output/'latest.json')
 # Stable entry point for convenient navigation; run folders retain history.
 (output/'dashboard.html').write_text(body,encoding='utf-8')
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--raw',type=Path,default=ROOT/'data/raw');parser.add_argument('--output',type=Path,default=ROOT/'reports');parser.add_argument('--as-of',default='2025-12-31');args=parser.parse_args()
 try:print(json.dumps(run(args.raw,args.output,args.as_of),indent=2))
 except Exception as exc:
  print(f'Pipeline failed; no successful manifest published: {exc}',file=sys.stderr);sys.exit(1)
