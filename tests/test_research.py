import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'research'))
from adapter import adapt, feature

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.row = {'query_index': 0, 'sample_index': 0, 'question':'Task', 'ground_truth':'HIDDEN', 'answer_text':'HIDDEN', 'final_label':-1,'step_labels':{'1':-1},'messages':[{'role':'user','content':'Task'},{'role':'assistant','content':'Checking','tool_calls':[{'id':'c1','function':{'name':'search','arguments':'{}'}}]},{'role':'tool','content':'Found','tool_call_id':'c1','name':'search'},{'role':'assistant','content':'FINAL_SECRET'}]}
    def test_reference_fields_never_used(self):
        a = feature(self.row,1); b=copy.deepcopy(self.row)
        for key in ['ground_truth','answer_text','final_label','step_labels']: b[key]='POISON'
        self.assertEqual(a, feature(b,1)); self.assertNotIn('HIDDEN',a); self.assertNotIn('FINAL_SECRET',a)
        self.assertNotIn('HIDDEN',json.dumps(adapt(self.row)))
    def test_future_and_final_exclusion(self):
        b=copy.deepcopy(self.row); b['messages'][2]['content']='FUTURE_POISON'
        self.assertEqual(feature(self.row,1),feature(b,1))
        with self.assertRaises(ValueError): feature(self.row,3)
        self.assertNotIn('FINAL_SECRET',json.dumps(adapt(self.row,exclude_final=True)))
    def test_tool_links(self):
        run=adapt(self.row); self.assertEqual(run['steps'][2]['call_id'],run['steps'][3]['call_id'])
    def test_frozen_split_and_counts(self):
        base=Path(__file__).resolve().parents[1]/'research'
        split=json.loads((base/'split.json').read_text()); result=json.loads((base/'results.json').read_text())
        self.assertEqual(len(split['groups']),200)
        self.assertEqual(sum(x['runs'] for x in result['split'].values()),1000)
        self.assertEqual(sum(x['steps'] for x in result['split'].values()),7509)
        self.assertEqual(split['source_sha256'],result['sha256'])

if __name__=='__main__': unittest.main()
