"""Synthetic driver review gates. No execute_fit call, sklearn import or fit."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experimental'))
import calibrate
from contract import artifact, encode

class CalibrationDriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
    def fixture(self, change=None):
        rows=[]
        for i in range(3):
            rows.append({'query_index':i,'sample_index':0,'question':f'Task {i}',
                         'step_labels':{'1':(-1,0,1)[i],'3':1},'messages':[
                             {'role':'user','content':'Review'},
                             {'role':'assistant','content':'Checking','tool_calls':[{'id':'call','function':{'name':'search','arguments':'{}'}}]},
                             {'role':'tool','tool_call_id':'call','content':'failed lookup'},
                             {'role':'assistant','content':'FINAL'}]})
        # TEST cannot be processed by adapter, feature extractor or label parser.
        rows[2]['messages']=None;rows[2]['step_labels']=None
        if change:change(rows)
        source=self.data/'synthetic.jsonl'
        source.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        split={'seed':42,'groups':{'synthetic:0':'train','synthetic:1':'validation','synthetic:2':'test'},'source_sha256':{source.name:calibrate.digest(source)}}
        path=self.root/'split.json';path.write_text(json.dumps(split))
        return path,calibrate.digest(path)
    def load(self, path, sha, independent_groups=3):
        return calibrate.load_verified(self.data,path,sha,source_groups=3,independent_groups=independent_groups,attempts=1)
    def test_test_rows_excluded_before_features_and_rules(self):
        path,sha=self.fixture();rows,metadata=self.load(path,sha)
        self.assertEqual([row['_split'] for row in rows],['train','validation'])
        self.assertEqual(metadata['routing_runs'],{'train':1,'validation':1,'test':1})
        seen=[];original=calibrate.feature
        def checked(row,index):
            self.assertNotEqual(row['_split'],'test');seen.append(row['_split']);return original(row,index)
        with patch.object(calibrate,'feature',side_effect=checked),calibrate.Bridge() as bridge:
            samples=calibrate.prepare(rows,bridge)
        self.assertEqual(seen,['train','validation']);self.assertEqual(len(samples),2)
        self.assertTrue(samples[1]['rule'])
        self.assertTrue(all(s['support_reason'] is None for s in samples))
        with self.assertRaisesRegex(ValueError,'TEST'):
            calibrate.prepare([{'_split':'test'}],None)
    def test_hash_membership_inventory_and_duplicate_guards(self):
        path,sha=self.fixture()
        with self.assertRaisesRegex(ValueError,'split hash'):self.load(path,'0'*64)
        source=self.data/'synthetic.jsonl';source.write_text(source.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'Source hash'):self.load(path,sha)
        path,sha=self.fixture();(self.data/'unexpected.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError,'inventory'):self.load(path,sha)
        (self.data/'unexpected.jsonl').unlink()
        path,sha=self.fixture(lambda rows:rows[1].update(query_index=0))
        with self.assertRaisesRegex(ValueError,'duplicate attempt'):self.load(path,sha)
        path,sha=self.fixture(lambda rows:rows[1].update(question=rows[0]['question']))
        with self.assertRaisesRegex(ValueError,'Cross-split'):self.load(path,sha,independent_groups=2)
        path,sha=self.fixture(lambda rows:rows[1].update(query_index=55))
        with self.assertRaisesRegex(ValueError,'Unknown group'):self.load(path,sha)
    def test_compatibility_and_unicode_abstain_without_losing_labels_groups(self):
        def change(rows):
            rows[0]['messages'][1]['content']='English “quotes” and an em dash —'
            rows[1]['messages'][1]['content']='x'*100001
        path,sha=self.fixture(change);rows,_=self.load(path,sha)
        with calibrate.Bridge() as bridge:samples=calibrate.prepare(rows,bridge)
        self.assertEqual([r['support_reason'] for r in samples],['unsupported-unicode','incompatible-envelope'])
        counts=calibrate.coverage(samples)
        for split,label in [('train','-1'),('validation','0')]:
            self.assertEqual(counts[split]['all']['steps'],1)
            self.assertEqual(counts[split]['all']['unsupported_steps'],1)
            self.assertEqual(counts[split]['all']['unsupported_task_groups'],1)
            self.assertEqual(counts[split]['by_subset']['synthetic']['by_label'][label]['unsupported_steps'],1)
        self.assertNotIn('English',json.dumps(counts))
    def test_source_parity_mismatch_stops_before_fit(self):
        path,sha=self.fixture();rows,_=self.load(path,sha)
        class WrongBridge:
            def ask(self,_):return {'compatible':True,'hashes':{'1':'wrong'},'rule_indices':[]}
        with self.assertRaisesRegex(ValueError,'parity'):calibrate.prepare(rows,WrongBridge())
    def stage(self):
        stage=self.root/'stage';stage.mkdir()
        candidate=encode(artifact(['aa'],[1],[[0],[0],[0]],[0,0,0]))
        (stage/'candidate.json').write_text(candidate)
        report={'status':'completed','artifact_ready':True,'artifact_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
                'gate':{'selected_threshold':.5,'candidates':[{'threshold':.5,'eligible':True}]}}
        (stage/'report.json').write_text(json.dumps(report));return stage,report
    def test_supervisor_failure_always_blocks_candidate_publication(self):
        stage,_=self.stage()
        failures=[{'exit_code':1,'stop_reason':None}, {'exit_code':0,'stop_reason':'rss'}, {'exit_code':0,'stop_reason':'wall-time'}]
        failures += [{'exit_code':0,'stop_reason':None,'elapsed_seconds':61}, {'exit_code':0,'stop_reason':None,'sampled_peak_group_rss_kib':524289}]
        for i,failure in enumerate(failures):
            resource={'elapsed_seconds':1,'sampled_peak_group_rss_kib':100,**failure}
            output=self.root/f'failure-{i}';report=calibrate.publish(stage,output,resource)
            self.assertFalse(report['artifact_ready']);self.assertFalse((output/'model.json').exists())
    def test_gate_and_digest_required_and_output_cannot_be_overwritten(self):
        stage,receipt=self.stage();resource={'exit_code':0,'stop_reason':None,'elapsed_seconds':1,'sampled_peak_group_rss_kib':100}
        output=self.root/'success';result=calibrate.publish(stage,output,resource)
        self.assertTrue(result['artifact_ready']);self.assertTrue((output/'model.json').is_file())
        with self.assertRaises(FileExistsError):calibrate.publish(stage,output,resource)
        receipt['gate']['candidates'][0]['eligible']=False;(stage/'report.json').write_text(json.dumps(receipt))
        result=calibrate.publish(stage,self.root/'denied',resource);self.assertFalse(result['artifact_ready'])
        receipt['gate']['candidates'][0]['eligible']=True;(stage/'report.json').write_text(json.dumps(receipt))
        (stage/'candidate.json').write_text('changed')
        result=calibrate.publish(stage,self.root/'corrupt',resource);self.assertFalse(result['artifact_ready'])
