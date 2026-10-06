"""Offline, synthetic-only encoder preflight. No benchmark input or fitting API.

Requires verified local model bytes and exact CPU dependency pins.
This module does not download, install, serve, activate or train anything.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import socket
import time
import sys
import tempfile
import platform
from bounded import run_bounded
from provenance import verify_lock
from publication import publish_preflight
from unittest.mock import patch
from contract import WEIGHTS,REVISION,parts_with_audit,allocate,mean_normalize,tool_call_token_audit

TEXTS=['Check the configuration.', 'Use “curly quotes” and an English dash — carefully.',
       'café résumé naïve', '日本語の設定を確認する', 'راجع الإعدادات', 'emoji 🙂 with a file path',
       'e\u0301 and é', '<script>alert(1)</script>', 'Repeated tool input. '*600]

def verify_local(directory):
    sizes=verify_lock(directory,REVISION)
    for name,(size,expected) in WEIGHTS.items():
        path=directory/name
        if any(parent.is_symlink() for parent in [path,*path.parents]) or not path.is_file() or path.stat().st_size!=size:raise ValueError('Approved local model files missing or invalid')
        with path.open('rb') as source:
            actual=hashlib.file_digest(source,'sha256').hexdigest()
        if actual!=expected:raise ValueError('Model hash mismatch')
        sizes[name]=size
    config=json.loads((directory/'config.json').read_text())
    pool=json.loads((directory/'1_Pooling/config.json').read_text())
    if config.get('model_type')!='bert' or config.get('hidden_size')!=384 or config.get('num_hidden_layers')!=6:raise ValueError('Unexpected architecture')
    if not pool.get('pooling_mode_mean_tokens') or any(pool.get(k) for k in ['pooling_mode_cls_token','pooling_mode_max_tokens','pooling_mode_mean_sqrt_len_tokens']):raise ValueError('Unexpected pooling')
    if json.loads((directory/'sentence_bert_config.json').read_text()).get('max_seq_length')!=256:raise ValueError('Unexpected sequence limit')
    return sizes

def run(directory):
    sizes=verify_local(directory)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',TOKENIZERS_PARALLELISM='false',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    started=time.monotonic()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Network disabled during local preflight')):
        import numpy as np
        import torch
        import onnxruntime as ort
        from tokenizers import Tokenizer
        from transformers import AutoTokenizer,AutoModel
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        hf=AutoTokenizer.from_pretrained(str(directory),local_files_only=True,trust_remote_code=False)
        tokenizer=Tokenizer.from_file(str(directory/'tokenizer.json'))
        tokenizer.no_truncation();tokenizer.no_padding()
        reference=AutoModel.from_pretrained(str(directory),local_files_only=True,trust_remote_code=False,use_safetensors=True).eval().cpu()
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
        session=ort.InferenceSession(str(directory/'onnx/model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        load_seconds=time.monotonic()-started
        inputs=[];unknown=[];truncation=[]
        rows=[]
        for text in TEXTS:
            row={'question':'Inspect the local project without changing files.','messages':[
                {'role':'user','content':'Inspect configuration'},
                {'role':'tool','content':'File exists; content follows.'},
                {'role':'assistant','content':text,'tool_calls':[{'function':{'name':'read_file','arguments':'{"path":"settings.json"}'}}]},
                {'role':'assistant','content':'FINAL EXCLUDED'}]}
            rows.append(row)
        # Exercise every character cap and task/prefix token allocation with the
        # real tokenizer. Appended calls disappear at both distinct cap stages.
        rows.append({'question':'task '*1000,'messages':[
            {'role':'user','content':'prefix '*1000,'tool_calls':[
                {'function':{'name':'context_file','arguments':'context '*1000}}]},
            {'role':'tool','content':'prior '*1000,'tool_calls':[
                {'function':{'name':'prior_file','arguments':'result '*1000}}]},
            {'role':'assistant','content':'action '*1000,'tool_calls':[
                {'function':{'name':'read_file','arguments':'argument '*1000}} for _ in range(4)]},
            {'role':'assistant','content':'FINAL EXCLUDED'}]})
        for case_index,row in enumerate(rows):
            p,audit=parts_with_audit(row,2);ids={}
            audit['case_index']=case_index
            for key,value in p.items():
                ids[key]=tokenizer.encode(value,add_special_tokens=False).ids
                assert ids[key]==hf.encode(value,add_special_tokens=False)
                unknown.append({'case_index':case_index,'field':key,'tokens':len(ids[key]),'unknown_tokens':ids[key].count(hf.unk_token_id)})
            allocated=allocate(ids['task'],ids['prefix'],ids['action'],hf.cls_token_id,hf.sep_token_id)
            audit['tokens']=allocated['token_counts']
            audit['action_tool_calls_after_token_limit']=tool_call_token_audit(tokenizer,p['action'],audit['action_tool_spans'],254)
            truncation.append(audit)
            inputs.extend([allocated['context'],allocated['action']])
        def arrays(batch):
            width=max(map(len,batch));values=np.full((len(batch),width),hf.pad_token_id,dtype=np.int64);mask=np.zeros_like(values)
            for i,ids in enumerate(batch):values[i,:len(ids)]=ids;mask[i,:len(ids)]=1
            return {'input_ids':values,'attention_mask':mask,'token_type_ids':np.zeros_like(values)}
        def encode_onnx(batch):
            values=arrays(batch);output=session.run(None,{i.name:values[i.name] for i in session.get_inputs()})[0]
            mask=values['attention_mask'][...,None].astype(np.float32)
            pooled=(output*mask).sum(axis=1)/np.maximum(mask.sum(axis=1),1e-9)
            norms=np.linalg.norm(pooled,axis=1,keepdims=True)
            if not np.isfinite(pooled).all() or (norms==0).any():raise ValueError('Invalid encoder output')
            return pooled/norms
        values=arrays(inputs)
        with torch.no_grad():
            output=reference(**{k:torch.from_numpy(v) for k,v in values.items()}).last_hidden_state
            mask=torch.from_numpy(values['attention_mask']).unsqueeze(-1)
            pooled=(output*mask).sum(1)/mask.sum(1).clamp(min=1e-9)
            expected=torch.nn.functional.normalize(pooled,p=2,dim=1).numpy()
        actual=encode_onnx(inputs)
        error=float(np.max(np.abs(actual-expected)))
        cosine=float(np.min(np.sum(actual*expected,axis=1)))
        assert actual.shape==(len(inputs),384) and error<=1e-4 and cosine>=.99999
        assert np.allclose(np.linalg.norm(actual,axis=1),1,atol=1e-5)
        # Ordered [context,action] 768-D vectors. No learned detector exists here.
        paired=actual.reshape(-1,768);assert paired.shape==(len(rows),768)
        # Handcrafted coefficients check deployable arithmetic, never a fit.
        coefficients=np.sin(np.arange(3*768,dtype=np.float64).reshape(3,768))*.01
        def synthetic_head(vectors):
            logits=vectors@coefficients.T+np.array([.2,-.1,0.])
            exp=np.exp(logits-logits.max(axis=1,keepdims=True));return exp/exp.sum(axis=1,keepdims=True)
        head_reference=synthetic_head(expected.reshape(-1,768));head_local=synthetic_head(paired)
        head_error=float(np.max(np.abs(head_reference-head_local)))
        assert head_error<=1e-6
        for threshold in [.5,.6,.7,.8,.9,.95]:
            assert np.array_equal(head_reference[:,0]>threshold,head_local[:,0]>threshold)
        measurements=[]
        for name,batch in [('representative',inputs[:8]),('max-length',[inputs[-1]]*8)]:
            encode_onnx(batch)  # One warm-up; three measurements, no model selection.
            times=[]
            for _ in range(3):
                t=time.monotonic();encode_onnx(batch);times.append(time.monotonic()-t)
            measurements.append({'name':name,'batch_size':8,'tokens':max(map(len,batch)),'seconds':times,'min_sequences_per_second':8/max(times)})
        return {'status':'synthetic-preflight-only','revision':REVISION,'files_bytes':sizes,'bundle_bytes':sum(sizes.values()),
                'deployment_model_files_bytes':sum(v for k,v in sizes.items() if k!='model.safetensors'),
                'environment':{'python':platform.python_version(),'platform':platform.platform(),'cpu_count':os.cpu_count(),'threads':1,'providers':session.get_providers()},
                'synthetic_cases':len(rows),
                'parameter_count':sum(p.numel() for p in reference.parameters()),'load_seconds':load_seconds,
                'truncation':truncation,'tokenizer_cases':len(unknown),'tokenizer_exact_match':True,'unicode_token_counts':unknown,
                'synthetic_head_score_max_absolute_error':head_error,'embedding_max_absolute_error':error,'minimum_cosine_agreement':cosine,'measurements':measurements,
                'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'elapsed_seconds':time.monotonic()-started,'packages':{name:importlib.metadata.version(name) for name in ['numpy','torch','transformers','tokenizers','onnxruntime','safetensors','huggingface-hub']},
                'benchmark_rows_encoded':0,'head_fits':0,'quality_claim':'None; pretrained embeddings are not a trained error detector.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--_supervised-worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output must be new')
    if args._supervised_worker:
        result=run(args.model_dir)
        with args.output.open('x') as output:json.dump(result,output,indent=2,allow_nan=False)
    else:
        with tempfile.TemporaryDirectory(prefix='tracecheck-synthetic-') as temporary:
            result_path=Path(temporary)/'result.json'
            supervised=run_bounded([sys.executable,str(Path(__file__).resolve()),'--model-dir',str(args.model_dir.resolve()),'--output',str(result_path),'--_supervised-worker'])
            try:
                publish_preflight(result_path,args.output,supervised)
            except (ValueError,OSError) as error:
                print(json.dumps({'status':'preflight-failed','reason':str(error),'supervision':supervised}),file=sys.stderr)
                raise SystemExit(1)
