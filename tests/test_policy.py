import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experimental'))
from policy import choose_threshold, THRESHOLDS

class PolicyTests(unittest.TestCase):
    def rows(self):
        return [{'split':'validation','group':'g','subset':'synthetic','label':-1,'rule':False,'score':.99} for _ in range(20)]
    def test_combined_gate_rejects_different_false_positives(self):
        rows=self.rows()+[
            {'split':'validation','group':'g','subset':'synthetic','label':1,'rule':True,'score':None},
            {'split':'validation','group':'g','subset':'synthetic','label':1,'rule':False,'score':.99}]
        result=choose_threshold(rows,{'g'})
        self.assertIsNone(result['selected_threshold'])
        self.assertEqual(result['candidates'][0]['model']['fp'],result['rules']['fp'])
        self.assertEqual(result['candidates'][0]['combined']['fp'],2)
    def test_predeclared_tiebreak_and_no_test_input(self):
        result=choose_threshold(self.rows(),{'g'})
        self.assertEqual([c['threshold'] for c in result['candidates']],list(THRESHOLDS))
        self.assertEqual(result['selected_threshold'],.95)
        for change in [lambda r:r.update(split='test'),lambda r:r.update(group='unseen'),lambda r:r.update(score=float('nan'))]:
            rows=copy.deepcopy(self.rows());change(rows[0])
            with self.assertRaises(ValueError):choose_threshold(rows,{'g'})
    def test_abstention_and_minimum_support(self):
        rows=self.rows();rows[0]['score']=None
        self.assertIsNone(choose_threshold(rows,{'g'})['selected_threshold'])

    def test_paired_task_counts_reconcile_and_preserve_abstentions(self):
        rows=self.rows()+[
            {'split':'validation','group':'h','subset':'synthetic','label':0,'rule':False,'score':.9},
            {'split':'validation','group':'h','subset':'synthetic','label':-1,'rule':True,'score':None},
            {'split':'validation','group':'g','subset':'synthetic','label':1,'rule':False,'score':None}]
        result=choose_threshold(rows,{'g','h'})
        policies=[result['rules'],result['never_flag']]+[c[k] for c in result['candidates'] for k in ('model','combined')]
        for policy in policies:
            self.assertEqual(set(policy['per_task_confusion']),{'g','h'})
            for key in ('tp','fp','fn','tn'):
                self.assertEqual(sum(v[key] for v in policy['per_task_confusion'].values()),policy[key])
            self.assertEqual(sum(sum(v.values()) for v in policy['per_task_confusion'].values()),len(rows))
        model=result['candidates'][0]['model']['per_task_confusion']
        self.assertEqual(model['g'],{'tp':20,'fp':0,'fn':0,'tn':1})
        self.assertEqual(model['h'],{'tp':0,'fp':1,'fn':1,'tn':0})
        self.assertIn('unassessed',result['uncertainty'])
