from contextlib import closing
import csv,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_pipeline import run,SCHEMAS

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.raw=self.root/'raw';self.raw.mkdir();self.out=self.root/'reports'
  self.rows={
   'vendors':[['V1','Vendor One',30]],'items':[['I1','Part',200,10]],
   'invoices':[['A','V1','2025-01-01','2025-01-31',10000],['B','V1','2025-01-01','2025-02-28',2000]],
   'payments':[['P1','A','2025-02-01',2500],['P2','A','2025-03-01',7500]],
   'purchase_orders':[['O1','V1','I1','2025-01-01','2025-01-15','2025-01-15',5],['O2','V1','I1','2025-01-01','2025-01-15','',5]],
   'inventory_movements':[['M1','I1','EDM','2025-01-01',10,'Opening'],['M2','I1','EDM','2025-02-01',-12,'Issue']]}
  self.write()
 def tearDown(self):self.temp.cleanup()
 def write(self):
  for name,(_,ddl) in SCHEMAS.items():
   headers=[c.strip().split()[0] for c in ddl.split(',')]
   with (self.raw/(name+'.csv')).open('w',newline='') as f:
    w=csv.writer(f);w.writerow(headers);w.writerows(self.rows[name])
 def result(self):return run(self.raw,self.out,'2025-02-28')
 def test_cutoff_aging_stock_and_order_denominator(self):
  result=self.result()
  with closing(sqlite3.connect(Path(result['output_folder'])/'erp_analysis.sqlite')) as db:
   self.assertEqual(db.execute("SELECT OpenCents FROM APDetail WHERE InvoiceID='A'").fetchone()[0],7500)
   self.assertEqual(db.execute("SELECT AgingBucket FROM APDetail WHERE InvoiceID='B'").fetchone()[0],'Current')
   self.assertEqual(db.execute('SELECT OnHand,Status FROM InventoryPosition').fetchone(),(-2,'Negative stock'))
   self.assertEqual(db.execute('SELECT ReceivedOrders,OnTimeOrders,OpenOverdueOrders FROM VendorPerformance').fetchone(),(1,1,1))
  self.assertTrue(all(result['checks'].values()))
 def test_identical_rerun_reuses_success(self):
  a=self.result();b=self.result();self.assertEqual(a['run_id'],b['run_id']);self.assertTrue(b['reused'])
 def test_exact_duplicate_does_not_double_invoice(self):
  self.rows['invoices'].append(self.rows['invoices'][0].copy());self.write();r=self.result()
  self.assertEqual(r['quality_exception_count'],1);self.assertEqual(r['source_counts']['Invoices']['accepted'],2)
 def test_conflicting_duplicate_fails_and_preserves_latest(self):
  self.result();before=(self.out/'latest.json').read_bytes()
  self.rows['invoices'].append(['A','V1','2025-01-01','2025-01-31',9999]);self.write()
  with self.assertRaisesRegex(ValueError,'Conflicting duplicate'):self.result()
  self.assertEqual(before,(self.out/'latest.json').read_bytes())
 def test_unknown_vendor_and_orphan_payment_quarantined(self):
  self.rows['invoices'].append(['C','V404','2025-01-01','2025-01-31',100])
  self.rows['payments'].append(['P3','C','2025-02-01',100]);self.write()
  self.assertEqual(self.result()['quality_exception_count'],2)
 def test_overpayment_is_visible(self):
  self.rows['payments'].append(['P3','B','2025-02-01',3000]);self.write();r=self.result()
  with closing(sqlite3.connect(Path(r['output_folder'])/'erp_analysis.sqlite')) as db:
   self.assertEqual(db.execute("SELECT OpenCents,AgingBucket FROM APDetail WHERE InvoiceID='B'").fetchone(),(-1000,'Credit / overpayment'))
 def test_missing_file_fails(self):
  (self.raw/'items.csv').unlink()
  with self.assertRaises(FileNotFoundError):self.result()
 def test_changed_cutoff_creates_new_run(self):
  a=self.result();b=run(self.raw,self.out,'2025-03-31');self.assertNotEqual(a['run_id'],b['run_id'])
if __name__=='__main__':unittest.main()
