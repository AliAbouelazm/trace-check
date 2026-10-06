import copy
import math
from pathlib import Path
import sys
import unittest
# Distinct module name avoids collision with the existing experimental contract.
import importlib.util
spec=importlib.util.spec_from_file_location('semantic_contract',Path(__file__).resolve().parents[1]/'semantic/contract.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class SemanticContractTests(unittest.TestCase):
    def test_ordered_parts_never_use_references_future_or_system_text(self):
        row={'question':'Allowed task','ground_truth':'SECRET','messages':[
            {'role':'system','content':'SYSTEM'}, {'role':'user','content':'Previous request'},
            {'role':'assistant','content':'Use “quotes” — safely','tool_calls':[
                {'function':{'name':'one','arguments':'first'}},{'function':{'name':'two','arguments':'second'}}]},
            {'role':'tool','content':'FUTURE'}, {'role':'assistant','content':'FINAL'}]}
        result=module.parts(row,2)
        self.assertEqual(result['task'],'Allowed task');self.assertEqual(result['prefix'],'user Previous request')
        self.assertTrue(result['action'].endswith('one first\ntwo second'))
        self.assertIn('“quotes” —',result['action'])
        self.assertNotIn('SECRET',str(result));self.assertNotIn('FUTURE',str(result));self.assertNotIn('SYSTEM',str(result))
        with self.assertRaises(ValueError):module.parts(row,4)
        with self.assertRaises(ValueError):module.parts(row,3)
    def test_fixed_wordpiece_allocation_keeps_task_prefix_order_and_action_separate(self):
        result=module.allocate(list(range(100)),list(range(300,600)),list(range(1000,1400)),101,102)
        self.assertEqual(len(result['context']),256);self.assertEqual(len(result['action']),256)
        self.assertEqual(result['context'][1:65],list(range(64)))
        self.assertEqual(result['context'][65:-1],list(range(410,600)))
        self.assertEqual(result['action'][1:-1],list(range(1000,1254)))
        self.assertTrue(all(result['truncated'].values()))
    def test_attention_masked_pooling_and_l2_normalization(self):
        actual=module.mean_normalize([[2.,0.],[0.,2.],[999.,999.]],[1,1,0])
        for v in actual:self.assertAlmostEqual(v,1/math.sqrt(2))
        with self.assertRaises(ValueError):module.mean_normalize([[1.,0.]],[0])
        with self.assertRaises(ValueError):module.mean_normalize([[float('nan'),0.]],[1])
