import unittest,sys,tempfile,json
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_pipeline import parse,run
class PaymentTests(unittest.TestCase):
 def row(self,**kw):return {'AMOUNT':'12.34','CHECK DATE':'07/31/2025','VENDOR NAME':'Vendor','CONTRACT NUMBER':'DV','VOUCHER NUMBER':'','DEPARTMENT NAME':'',**kw}
 def test_cent_precision(self):self.assertEqual(parse(self.row())[-1],1234)
 def test_missing_department_not_invented(self):self.assertEqual(parse(self.row())[-2],'Not reported')
 def test_annual_rollup_has_no_date(self):self.assertEqual(parse(self.row(**{'CHECK DATE':'2002'}))[:3],(2002,'','Annual rollup'))
 def test_negative_preserved(self):self.assertEqual(parse(self.row(AMOUNT='-1.01'))[-1],-101)
 def test_invalid_date_rejected(self):
  with self.assertRaises(ValueError):parse(self.row(**{'CHECK DATE':'02/30/2025'}))
 def test_fractional_cent_rejected(self):
  with self.assertRaises(ValueError):parse(self.row(AMOUNT='1.001'))
 def test_failed_build_preserves_published_report(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);(out/'manifest.json').write_text('{"run_id":"previous"}');(out/'dashboard.html').write_text('Previous report')
   with patch('run_pipeline.fingerprint',return_value='changed'),patch('run_pipeline._build',side_effect=ValueError('bad source')):
    with self.assertRaises(ValueError):run(out)
   self.assertEqual((out/'dashboard.html').read_text(),'Previous report');self.assertEqual(json.loads((out/'manifest.json').read_text())['run_id'],'previous')
 def test_completed_run_reused_without_reprocessing(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);folder=out/'runs/fixed';folder.mkdir(parents=True);(folder/'manifest.json').write_text('{"run_id":"fixed","reused":false}');(folder/'dashboard.html').write_text('Completed')
   with patch('run_pipeline.fingerprint',return_value='fixed'),patch('run_pipeline._build') as build:
    self.assertTrue(run(out)['reused']);build.assert_not_called()
   self.assertEqual((out/'dashboard.html').read_text(),'Completed')
if __name__=='__main__':unittest.main()
