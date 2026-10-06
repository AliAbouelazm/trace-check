"""No encoder imports, network, benchmark records or fits."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('semantic_'+name,ROOT/'semantic'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
publication=load('publication');bounded=load('bounded');provenance=load('provenance');contract=load('contract')

class SemanticPreflightTests(unittest.TestCase):
    def test_limits_kill_timeout_memory_and_refuse_increases(self):
        for options in [{'seconds':121},{'rss_mib':2049}]:
            with self.assertRaises(ValueError):bounded.run_bounded(['unused'],**options)
        ok=bounded.run_bounded([sys.executable,'-c','pass'])
        self.assertEqual(ok['exit_code'],0);self.assertIsNone(ok['stop_reason'])
        result=bounded.run_bounded([sys.executable,'-c','import time; time.sleep(5)'],seconds=.05)
        self.assertEqual(result['stop_reason'],'wall-time')
        result=bounded.run_bounded([sys.executable,'-c','import time; x=bytearray(8000000); time.sleep(5)'],rss_mib=1)
        self.assertEqual(result['stop_reason'],'rss')
    def test_unverified_lock_blocks_normal_cli_before_encoder_import(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'result.json'
            result=subprocess.run([sys.executable,str(ROOT/'semantic/preflight.py'),'--model-dir',directory,'--output',str(output)],capture_output=True,text=True,timeout=5)
            self.assertNotEqual(result.returncode,0);self.assertFalse(output.exists())
            self.assertIn('Verified source/runtime pins required',result.stderr)
            self.assertIn('preflight-failed',result.stderr)
    def test_all_small_files_exact_hash_versions_and_symlinks_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);files={}
            for name in provenance.REQUIRED_FILES:
                path=directory/name;path.parent.mkdir(exist_ok=True);path.write_bytes(b'{}')
                files[name]={'bytes':2,'sha256':hashlib.sha256(b'{}').hexdigest(),'source':'https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/'+contract.REVISION+'/'+name}
            lock={'verified':True,'revision':contract.REVISION,'files':files,'packages':dict.fromkeys(provenance.REQUIRED_PACKAGES,'1.0')}
            lock_path=directory/'lock.json';lock_path.write_text(json.dumps(lock))
            self.assertEqual(len(provenance.verify_lock(directory,contract.REVISION,lock_path,lambda _: '1.0')),9)
            with self.assertRaisesRegex(ValueError,'dependency'):provenance.verify_lock(directory,contract.REVISION,lock_path,lambda _: '2.0')
            (directory/'tokenizer.json').write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError,'digest'):provenance.verify_lock(directory,contract.REVISION,lock_path,lambda _: '1.0')
            (directory/'tokenizer.json').unlink();(directory/'tokenizer.json').symlink_to(directory/'config.json')
            with self.assertRaisesRegex(ValueError,'Symlink'):provenance.verify_lock(directory,contract.REVISION,lock_path,lambda _: '1.0')
    def test_character_and_token_losses_include_appended_calls(self):
        row={'question':'q'*5000,'messages':[{'role':'user','content':'p'*5000},{'role':'assistant','content':'a'*5000,'tool_calls':[{'function':{'name':'read','arguments':'x'*5000}} for _ in range(4)]},{'role':'assistant','content':'final'}]}
        parts,audit=contract.parts_with_audit(row,1)
        self.assertEqual(len(parts['action']),12000)
        self.assertEqual(audit['characters']['task']['removed'],1000)
        self.assertEqual(audit['message_fields']['action']['fields'][0]['characters_before'],5000)
        self.assertTrue(audit['action_tool_spans'][-1]['removed_entirely'])
        self.assertGreater(audit['action_tool_spans'][1]['characters_retained'],0)
        tokens=contract.allocate(range(70),range(200),range(300),101,102)['token_counts']
        self.assertEqual(tokens['action']['removed'],46)
        self.assertEqual(tokens['prefix']['removed'],10)

    def test_tool_calls_removed_by_token_limit_are_counted(self):
        class Encoding:
            offsets=[(i,i+1) for i in range(300)]
        class SyntheticTokenizer:
            def encode(self,text,add_special_tokens=False):return Encoding()
        result=contract.tool_call_token_audit(SyntheticTokenizer(),'a'*300,[{'index':0,'start':250,'end':270},{'index':1,'start':280,'end':300},{'index':2,'start':310,'end':330}],254)
        self.assertEqual(result[0]['tokens_before_limit'],20)
        self.assertEqual(result[0]['tokens_retained'],4)
        self.assertFalse(result[0]['removed_entirely'])
        self.assertEqual(result[1]['tokens_retained'],0)
        self.assertTrue(result[1]['removed_entirely'])
        self.assertTrue(result[2]['removed_entirely'])

    def test_final_publication_rejects_successful_exit_over_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage=Path(temporary)/'stage.json';output=Path(temporary)/'published.json'
            # Invalid staged JSON proves resource rejection happens before reading it.
            stage.write_text('not JSON')
            base={'exit_code':0,'stop_reason':None,'elapsed_seconds':120,'sampled_peak_group_rss_kib':2048*1024}
            cases=[{'elapsed_seconds':120.000001},{'sampled_peak_group_rss_kib':2048*1024+1},
                   {'elapsed_seconds':-1},{'elapsed_seconds':float('nan')},{'elapsed_seconds':float('inf')},
                   {'sampled_peak_group_rss_kib':-1},{'sampled_peak_group_rss_kib':float('nan')},
                   {'sampled_peak_group_rss_kib':float('inf')},{'elapsed_seconds':None},
                   {'sampled_peak_group_rss_kib':True},{'exit_code':1},{'stop_reason':'wall-time'}]
            for change in cases:
                with self.subTest(change=change):
                    with self.assertRaisesRegex(ValueError,'Final preflight resource'):
                        publication.publish_preflight(stage,output,{**base,**change})
                    self.assertFalse(output.exists())
            stage.write_text(json.dumps({'status':'synthetic-preflight-only','benchmark_rows_encoded':0,'head_fits':0}))
            publication.publish_preflight(stage,output,base)
            self.assertEqual(json.loads(output.read_text())['supervision'],base)
            with self.assertRaises(FileExistsError):publication.publish_preflight(stage,output,base)
