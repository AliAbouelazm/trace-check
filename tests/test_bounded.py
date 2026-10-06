from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experimental'))
from bounded import run_bounded

class BoundedTests(unittest.TestCase):
    def test_harmless_process_and_budget_escalation_rejection(self):
        result=run_bounded([sys.executable,'-c','pass'])
        self.assertEqual(result['exit_code'],0)
        self.assertIsNone(result['stop_reason'])
        with self.assertRaises(ValueError):run_bounded(['unused'],seconds=61)
        with self.assertRaises(ValueError):run_bounded(['unused'],rss_mib=513)
    def test_timeout_and_memory_stop_without_fits(self):
        result=run_bounded([sys.executable,'-c','import time; time.sleep(5)'],seconds=.05)
        self.assertEqual(result['stop_reason'],'wall-time')
        result=run_bounded([sys.executable,'-c','import time; x=bytearray(8*1024*1024); time.sleep(5)'],rss_mib=1)
        self.assertEqual(result['stop_reason'],'rss')
