import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experimental'))
from contract import artifact, encode, reference_feature
from fixtures import fixtures
from adapter import feature

class ExperimentalTests(unittest.TestCase):
    def test_export_json_bounds_and_finiteness(self):
        with self.assertRaises(ValueError):artifact(['x'],[float('nan')],[[0],[0],[0]],[0,0,0])
        with self.assertRaises(ValueError):artifact(['x'],[1],[[0],[0],[0]],[0,0,0],threshold=.55)
        with self.assertRaises(ValueError):encode('x'*(2*1024*1024))
        model=fixtures()['model']
        self.assertEqual(json.loads(encode(model)),model)
    def test_multiple_call_source_feature_matches_reconstructed_groups(self):
        from contract import make_envelope
        row={'query_index':0,'sample_index':0,'question':'Task','messages':[
            {'role':'user','content':'Earlier'},
            {'role':'assistant','content':{'nested':'value'},'tool_calls':[
                {'function':{'name':'one','arguments':{'value':2,'unicode':'é'}}},
                {'function':{'name':'two','arguments':None}}]},
            {'role':'system','content':'EXCLUDED'},
            {'role':'assistant','content':'Current'},
            {'role':'assistant','content':'FINAL'}]}
        envelope=make_envelope(row)
        for index in [1,3]:self.assertEqual(reference_feature(envelope,index),feature(row,index))
        poison=copy.deepcopy(row)
        poison.update(ground_truth='POISON',answer_text='POISON',step_labels={'1':-1},final_label=-1)
        self.assertEqual(make_envelope(poison),envelope)
