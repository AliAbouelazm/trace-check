"""Synthetic-only v2 contract and driver tests. No real encoder or classifier fit."""
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import types
import warnings
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from semantic import features,fit,data

class Tokens:
    def token_to_id(self,name):return {'[CLS]':101,'[SEP]':102,'[UNK]':100}[name]
    def encode(self,value,add_special_tokens=False):
        class Encoded:pass
        result=Encoded();result.ids=[100 if word=='???' else 1000+sum(map(ord,word)) for word in value.split()];return result

def row(calls=4):
    return {'question':'task '*1000,'messages':[{'role':'user','content':'prior '*1000},
        {'role':'assistant','content':'prose '*1000,'tool_calls':[
            {'function':{'name':f'tool{i}','arguments':'HEAD '+('middle '*1000)+'TAIL'}} for i in range(calls)]},
        {'role':'assistant','content':'SECRET FINAL'}]}

class V2Tests(unittest.TestCase):
    def test_parallel_names_head_tail_and_text_each_survive(self):
        prepared,chars=features.prepare_input(row(),1);streams,audit=features.tokenize(prepared,Tokens())
        self.assertIsNone(audit['support_reason']);self.assertLessEqual(len(streams['action']),256)
        self.assertEqual(audit['fields']['text']['retained'],94)
        for i,call in enumerate(audit['calls']):
            self.assertEqual(call['name']['retained'],1);self.assertEqual(call['arguments']['retained'],31)
            self.assertIn(Tokens().encode(f'tool{i}').ids[0],streams['action'])
        self.assertEqual(streams['action'].count(Tokens().encode('HEAD').ids[0]),4)
        self.assertEqual(streams['action'].count(Tokens().encode('TAIL').ids[0]),4)
        self.assertGreater(chars['calls'][0]['argument_characters']['removed'],0)
        self.assertEqual(streams['action'][1:95],Tokens().encode(prepared['text']).ids[:94])
    def test_abstains_when_any_call_cannot_be_represented(self):
        for calls,change,reason in [(5,None,'more-than-four'),(4,'long-name','tool-name-exceeds'),(4,'unknown-name','unknown-or-empty'),(4,'unknown-args','unknown-only')]:
            example=row(calls)
            if change:
                function=example['messages'][1]['tool_calls'][-1]['function']
                if change=='long-name':function['name']='name '*10
                elif change=='unknown-name':function['name']='???'
                else:function['arguments']='??? ???'
            prepared,_=features.prepare_input(example,1);_,audit=features.tokenize(prepared,Tokens())
            self.assertTrue(audit['support_reason'].startswith(reason))
    def test_unicode_and_label_future_invariance(self):
        example=row(1);example['messages'][1]['content']='日本語 café العربية 🙂'
        example['messages'][1]['tool_calls'][0]['function']['arguments']='开始 café конец'
        original=features.prepare_input(example,1)
        example.update(step_labels={'1':-1},ground_truth='SECRET',final_label=-1)
        example['messages'][-1]['content']='CHANGED FINAL'
        self.assertEqual(original,features.prepare_input(example,1))
        _,audit=features.tokenize(original[0],Tokens());self.assertIsNone(audit['support_reason'])
        with self.assertRaises(ValueError):features.prepare_input(example,2)
    def test_cache_keys_isolate_split_inputs_revision_and_labels(self):
        sample={'split':'train','input_sha256':'abc','streams':{'context':[101,102],'action':[101,123,102]}}
        identity={'feature_code_sha256':'def','source_sha256':{'a':'a'*64}}
        key=fit.cache_key(sample,identity)
        self.assertEqual(key,fit.cache_key({**sample,'label':-1},identity))
        self.assertNotEqual(key,fit.cache_key({**sample,'split':'validation'},identity))
        self.assertNotEqual(key,fit.cache_key({**sample,'input_sha256':'changed'},identity))
        with patch.object(fit,'REVISION','changed'):self.assertNotEqual(key,fit.cache_key(sample,identity))
        with self.assertRaises(ValueError):fit.cache_key({**sample,'split':'test'},identity)
    def test_test_exclusion_before_parsing_labels_or_messages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'synthetic.jsonl'
            rows=[{'query_index':i,'sample_index':0,'question':str(i),'messages':None,'step_labels':None} for i in range(3)]
            source.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            split=root/'split.json';split.write_text(json.dumps({'groups':{'synthetic:0':'train','synthetic:1':'validation','synthetic:2':'test'},'source_sha256':{source.name:data.digest(source)}}))
            loaded,meta=data.load_verified(root,split,data.digest(split),source_groups=3,independent_groups=3,attempts=1)
            self.assertEqual([r['_split'] for r in loaded],['train','validation'])
            self.assertEqual(sum(map(len,meta['groups_by_split'].values())),3)
            with self.assertRaisesRegex(ValueError,'TEST'):fit.prepare([{'_split':'test'}],None,None)
            source.write_text(source.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'Source hash'):data.load_verified(root,split,data.digest(split),source_groups=3,independent_groups=3,attempts=1)
    def test_combined_fp_gate_unchanged_and_empty_groups_retained(self):
        rows=[{'split':'validation','group':'task','subset':'fixture','label':-1,'rule':False,'score':.99} for _ in range(21)]
        rows.append({'split':'validation','group':'task','subset':'fixture','label':0,'rule':False,'score':.99})
        gate=fit.evaluate(rows,['task','empty'])
        self.assertIsNone(gate['selected_threshold'])
        for candidate in gate['candidates']:
            self.assertFalse(candidate['eligible']);self.assertEqual(candidate['combined']['fp'],1)
            self.assertEqual(candidate['model']['per_task_confusion']['empty'],dict.fromkeys(('tp','fp','fn','tn'),0))
        rows[-1]['score']=None
        self.assertEqual(fit.evaluate(rows,['task','empty'])['selected_threshold'],.95)
    def test_exactly_one_train_fit_no_validation_or_unsupported_labels(self):
        samples=[{'split':'train','support_reason':None,'label':label} for label in (-1,0,1)]
        samples += [{'split':'validation','support_reason':None,'label':-1},{'split':'train','support_reason':'unsupported','label':-1}]
        calls=[]
        class Matrix:
            def __getitem__(self,indices):return indices
        class Model:
            def fit(self,x,y):calls.append((x,y))
        def factory(**kwargs):
            self.assertEqual(kwargs,{'C':1.0,'solver':'lbfgs','max_iter':500,'class_weight':None,'random_state':42,'tol':1e-4})
            return Model()
        with patch.dict(sys.modules,{'sklearn.exceptions':types.SimpleNamespace(ConvergenceWarning=UserWarning)}):
            fit.fit_head(Matrix(),samples,factory)
        self.assertEqual(calls,[([0,1,2],[-1,0,1])])
        with self.assertRaisesRegex(ValueError,'TEST'):fit.fit_head(Matrix(),samples+[{'split':'test'}],factory)
        self.assertEqual(len(calls),1)
        with self.assertRaisesRegex(ValueError,'all classes'):fit.fit_head(Matrix(),samples[1:],factory)
    def test_convergence_warning_before_iteration_limit_aborts_sole_fit(self):
        samples=[{'split':'train','support_reason':None,'label':label} for label in (-1,0,1)]
        calls=[]
        class StubConvergenceWarning(UserWarning):pass
        class Matrix:
            def __getitem__(self,indices):return indices
        class Model:
            n_iter_=[2]  # Abnormal stop can precede the 500-iteration ceiling.
            def fit(self,x,y):
                calls.append((x,y))
                warnings.warn('abnormal solver stop',StubConvergenceWarning)
                calls.append('returned after warning')
        before=list(warnings.filters)
        with patch.dict(sys.modules,{'sklearn.exceptions':types.SimpleNamespace(ConvergenceWarning=StubConvergenceWarning)}):
            with self.assertRaisesRegex(StubConvergenceWarning,'abnormal solver stop'):
                fit.fit_head(Matrix(),samples,lambda **kwargs:Model())
        self.assertEqual(calls,[([0,1,2],[-1,0,1])])
        self.assertEqual(warnings.filters,before)

    def test_evidence_never_exports_source_text_tokens_or_input_hash(self):
        prepared,audit=features.prepare_input(row(),1);streams,tokens=features.tokenize(prepared,Tokens());audit['tokens']=tokens
        record={'split':'validation','subset':'fixture','group':'fixture:0','query_index':0,'sample_index':0,'message_index':1,'label':-1,'rule':False,'score':.9,'support_reason':None,'audit':audit,'streams':streams,'input_sha256':'secret hash','text':'SECRET RAW LOG'}
        evidence=fit.positional_evidence([record]);text=json.dumps(evidence)
        for secret in ('SECRET RAW LOG','secret hash','prose','tool0','HEAD','TAIL'):
            self.assertNotIn(secret,text)
        self.assertTrue(evidence[0]['text_redacted'])
    def test_fit_supervisor_kills_and_refuses_cap_increase(self):
        from semantic.fit_bounded import run_bounded
        with self.assertRaises(ValueError):run_bounded(['unused'],seconds=2211)
        with self.assertRaises(ValueError):run_bounded(['unused'],rss_mib=2049)
        result=run_bounded([sys.executable,'-c','import time; time.sleep(5)'],seconds=.05)
        self.assertEqual(result['stop_reason'],'wall-time')
        result=run_bounded([sys.executable,'-c','import time; x=bytearray(8000000); time.sleep(5)'],rss_mib=1)
        self.assertEqual(result['stop_reason'],'rss')

    def test_resource_and_publication_fail_closed(self):
        base={'exit_code':0,'stop_reason':None,'elapsed_seconds':2210,'sampled_peak_group_rss_kib':2048*1024}
        self.assertTrue(fit.resources_ok(base))
        for key,value in [('elapsed_seconds',2210.1),('elapsed_seconds',float('nan')),('elapsed_seconds',True),('sampled_peak_group_rss_kib',2048*1024+1),('exit_code',False),('stop_reason','rss')]:
            self.assertFalse(fit.resources_ok({**base,key:value}))
        with tempfile.TemporaryDirectory() as temporary:
            stage=Path(temporary)/'stage';stage.mkdir();output=Path(temporary)/'out'
            (stage/'report.json').write_text('not JSON')
            with self.assertRaisesRegex(ValueError,'resource'):fit.publish(stage,output,{**base,'elapsed_seconds':2211},time.monotonic())
            self.assertFalse(output.exists())
            (stage/'report.json').write_text(json.dumps({'status':'completed','head_fits':1,'artifact_ready':False}))
            with self.assertRaisesRegex(ValueError,'wall-time'):fit.publish(stage,output,base,time.monotonic()-2211)
            self.assertFalse(output.exists())
            fit.publish(stage,output,base,time.monotonic());self.assertTrue((output/'report.json').exists())
    def test_publication_rechecks_gate_inventory_pins_and_digest(self):
        from semantic import contract
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'semantic').mkdir()
            (root/'semantic/runtime-lock.json').write_text(json.dumps({'files':{}}))
            rows=[{'split':'validation','group':'task','subset':'fixture','label':-1,'rule':False,'score':.99} for _ in range(20)]
            resource={'exit_code':0,'stop_reason':None,'elapsed_seconds':1,'sampled_peak_group_rss_kib':100}
            def make_stage(name):
                stage=root/name;bundle=stage/'candidate';bundle.mkdir(parents=True)
                for filename in ('onnx/model.onnx','notices/NOTICE.txt','notices/LICENSE-2.0.txt','notices/all-MiniLM-L6-v2-model-card.md','fit-protocol.json','runtime-lock.json'):
                    path=bundle/filename;path.parent.mkdir(exist_ok=True);path.write_text('x')
                (bundle/'head.json').write_text(json.dumps({'threshold':.95,'feature_version':fit.FEATURE_VERSION,'encoder_revision':fit.REVISION}))
                files={str(p.relative_to(bundle)):{'bytes':p.stat().st_size,'sha256':data.digest(p)} for p in bundle.rglob('*') if p.is_file()}
                report={'status':'completed','head_fits':1,'artifact_ready':True,'gate':fit.evaluate(rows,['task']),
                        'evidence':rows,'provenance':{'validation_groups':['task']},'artifact_files':files,'artifact_bytes':sum(v['bytes'] for v in files.values())}
                (stage/'report.json').write_text(json.dumps(report));return stage,report
            with patch.object(fit,'ROOT',root),patch.dict(contract.WEIGHTS,{'onnx/model.onnx':(1,hashlib.sha256(b'x').hexdigest())}):
                stage,report=make_stage('success');output=root/'output'
                fit.publish(stage,output,resource,time.monotonic());self.assertTrue((output/'candidate/head.json').exists())
                stage,report=make_stage('changed');(stage/'candidate/head.json').write_text('corrupt')
                with self.assertRaises((ValueError,json.JSONDecodeError)):fit.publish(stage,root/'denied',resource,time.monotonic())
                self.assertFalse((root/'denied').exists())
                stage,report=make_stage('fake-gate');report['evidence'][0]={**report['evidence'][0],'label':0}
                (stage/'report.json').write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError,'gate mismatch'):fit.publish(stage,root/'denied2',resource,time.monotonic())
                self.assertFalse((root/'denied2').exists())

    def test_cli_requires_explicit_execution_approval_before_data_access(self):
        result=subprocess.run([sys.executable,str(ROOT/'semantic/fit.py'),'--data','/does-not-exist','--model-dir','/does-not-exist','--output','/does-not-exist'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('Parent execution approval',result.stderr)

if __name__=='__main__':unittest.main()
