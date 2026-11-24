"""Validate and summarize actual City of Chicago vendor-payment disclosures."""
import csv,gzip,json,sqlite3,hashlib,datetime,argparse,tempfile,shutil
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def parse(row):
 value=Decimal(row['AMOUNT'])*100
 if not value.is_finite() or value!=value.to_integral_value():raise ValueError('Invalid cent amount')
 date=row['CHECK DATE'];precision='Annual rollup' if len(date)==4 else 'Dated record'
 if precision=='Annual rollup':year=int(date);iso=''
 else:d=datetime.datetime.strptime(date,'%m/%d/%Y').date();year=d.year;iso=d.isoformat()
 if not 1996<=year<=2100:raise ValueError('Invalid year')
 vendor=row['VENDOR NAME'].strip()
 if not vendor:raise ValueError('Missing vendor')
 return year,iso,precision,vendor,row['CONTRACT NUMBER'].strip(),row['VOUCHER NUMBER'].strip(),row['DEPARTMENT NAME'].strip() or 'Not reported',int(value)
def _build(output=None):
 output=output or ROOT/'reports';output.mkdir(parents=True,exist_ok=True);source=ROOT/'data/source/chicago_payments.csv.gz'
 runid=fingerprint()
 pointer=output/'manifest.json'
 if pointer.exists() and json.loads(pointer.read_text())['run_id']==runid and (output/'dashboard.html').exists():
  result=json.loads(pointer.read_text());result['reused']=True;return result
 db=sqlite3.connect(output/'erp_analysis.sqlite');db.executescript('DROP TABLE IF EXISTS Payments;CREATE TABLE Payments(SourceRow INTEGER PRIMARY KEY,Year INTEGER,Date TEXT,Precision TEXT,Vendor TEXT,Contract TEXT,Voucher TEXT,Department TEXT,AmountCents INTEGER);')
 raw=accepted=0;issues=[];batch=[];seen=set();repeated=0
 with gzip.open(source,'rt',encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):
   raw+=1
   try:record=parse(row)
   except (ValueError,ArithmeticError) as exc:issues.append([raw+1,str(exc)]);continue
   # Voucher is not a reliable unique key. Preserve disclosures, flag exact repeats for review.
   key=hashlib.sha256(json.dumps(record).encode()).digest()
   if key in seen:repeated+=1
   seen.add(key);accepted+=1;batch.append((raw+1,*record))
   if len(batch)>=10000:db.executemany('INSERT INTO Payments VALUES(?,?,?,?,?,?,?,?,?)',batch);batch=[]
 if batch:db.executemany('INSERT INTO Payments VALUES(?,?,?,?,?,?,?,?,?)',batch)
 db.executescript((ROOT/'sql/analysis.sql').read_text());db.commit()
 def query(sql):
  c=db.execute(sql);return [dict(zip([x[0] for x in c.description],r)) for r in c]
 years=query('SELECT * FROM AnnualReview ORDER BY Year');monthly=query('SELECT * FROM MonthlyReview ORDER BY Month');vendors=query('SELECT * FROM VendorReview ORDER BY Year,PositiveCents DESC');departments=query('SELECT * FROM DepartmentReview ORDER BY Year,NetCents DESC');latest=max(r['Year'] for r in years)
 totals=query("SELECT COUNT(*) Rows,SUM(AmountCents) NetCents,SUM(CASE WHEN Precision='Annual rollup' THEN 1 ELSE 0 END) RollupRows,SUM(CASE WHEN Department='Not reported' THEN 1 ELSE 0 END) MissingDepartmentRows,SUM(CASE WHEN AmountCents<0 THEN 1 ELSE 0 END) NegativeRows,MAX(Date) LatestDatedRecord FROM Payments")[0]
 dated_total=db.execute("SELECT SUM(AmountCents) FROM Payments WHERE Precision='Dated record'").fetchone()[0]
 checks={'source_row_accounting':raw==accepted+len(issues),'annual_reconciliation':sum(r['NetCents'] for r in years)==totals['NetCents'],'monthly_dated_only_reconciliation':sum(r['NetCents'] for r in monthly)==dated_total,'vendor_reconciliation':sum(r['NetCents'] for r in vendors)==totals['NetCents'],'department_reconciliation':sum(r['NetCents'] for r in departments)==totals['NetCents'],'database_row_accounting':totals['Rows']==accepted}
 assert all(checks.values()),checks
 for name,rows in [('annual_summary.csv',years),('monthly_summary.csv',monthly),('vendor_summary.csv',vendors),('department_summary.csv',departments)]:
  with (output/name).open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 actions=[['Missing departments',totals['MissingDepartmentRows'],'Data steward','Confirm source coverage before department comparisons'],['Exact repeated records',repeated,'AP reviewer','Compare vouchers and source rows; do not assume duplicate payment'],['Negative amounts',totals['NegativeRows'],'AP reviewer','Inspect signed entries before interpreting gross and net spend'],['Annual rollups',totals['RollupRows'],'Analyst','Keep annual summaries out of monthly transaction counts'],['Rejected records',len(issues),'Data steward','Inspect quarantined source records']]
 with (output/'action_queue.csv').open('w',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(['Finding','Rows','OwnerRole','NextAction']);w.writerows(actions)
 with (output/'data_quality_exceptions.csv').open('w',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(['SourceRow','Reason']);w.writerows(issues)
 result={'run_id':runid,'source_rows':raw,'accepted_rows':accepted,'rejected_rows':len(issues),'exact_repeats_retained':repeated,'status':'needs_review','reused':False,'latest_year':latest,'totals':totals,'checks':checks}
 data={'years':years,'monthly':monthly,'vendors':vendors,'departments':departments,'manifest':result}
 (output/'dashboard_data.json').write_text(json.dumps(data),encoding='utf-8')
 (output/'dashboard.html').write_text((ROOT/'src/dashboard_template.html').read_text(encoding='utf-8').replace('__DATA__',json.dumps(data).replace('</',r'<\/')),encoding='utf-8')
 brief=f"# Chicago vendor-payment review\n\nObserved extract: {raw:,} source rows, {totals['RollupRows']:,} annual rollups, latest dated record {totals['LatestDatedRecord']}. Net disclosed amount across the entire extract: USD {totals['NetCents']/100:,.2f}. This includes historical periods and is not an annual budget.\n\nDepartment is absent on {totals['MissingDepartmentRows']:,} records; retain them under Not reported. Review {repeated:,} exact repeated records without asserting fraud or duplicate disbursement. Source vouchers are not unique invoice keys.\n\nHistorical records are aggregated by vendor and contract; 2002 includes 1996–2002. Monthly analysis uses dated records only. The latest year is partial. Signed amounts are preserved. The extract contains no invoice due dates, open balances, stock movements or promised delivery dates: AP aging, inventory and late-payment KPIs cannot be calculated. Business Central and Power Automate are deployment targets, not source systems used here.\n"
 (output/'management_brief.md').write_text(brief,encoding='utf-8')
 # Publish the success marker last; failed builds do not claim a completed run.
 temp=output/'manifest.tmp';temp.write_text(json.dumps(result,indent=2));temp.replace(pointer);db.close();return result
def fingerprint():
 return hashlib.sha256(b''.join(p.read_bytes() for p in [ROOT/'data/source/chicago_payments.csv.gz',Path(__file__),ROOT/'sql/analysis.sql',ROOT/'src/dashboard_template.html'])).hexdigest()[:20]
def run(output=None):
 output=output or ROOT/'reports';output.mkdir(parents=True,exist_ok=True)
 pointer=output/'manifest.json';runid=fingerprint();runfolder=output/'runs'/runid
 if (runfolder/'manifest.json').exists():
  result=json.loads((runfolder/'manifest.json').read_text());result['reused']=True
 else:
  with tempfile.TemporaryDirectory(prefix='erp-stage-') as temp:
   staging=Path(temp);result=_build(staging)
   runfolder.parent.mkdir(parents=True,exist_ok=True)
   shutil.copytree(staging,runfolder)
 # Publish copies only from a completed immutable run. Build failure leaves previous report intact.
 for p in runfolder.iterdir():
  if p.name=='manifest.json':continue
  temp=output/(p.name+'.tmp');shutil.copyfile(p,temp);temp.replace(output/p.name)
 temp=output/'manifest.tmp';temp.write_text(json.dumps(result,indent=2));temp.replace(pointer)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();print(json.dumps(run(a.output),indent=2))
