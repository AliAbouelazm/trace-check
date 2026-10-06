"""Review-only one-fit CLI. Never execute on benchmark data without parent approval."""
import argparse
import collections
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from semantic.contract import REVISION
from semantic.features import FEATURE_VERSION,prepare_input,tokenize
from semantic.data import SPLIT_SHA,digest,load_verified
from semantic.fit_bounded import run_bounded
from experimental.policy import choose_threshold,THRESHOLDS
from research.adapter import adapt

WALL_SECONDS=2210
RSS_KIB=2048*1024
ARTIFACT_BYTES=128*1024*1024
REPORT_BYTES=32*1024*1024
CACHE_BYTES=32*1024*1024
MAX_TARGETS=6214

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(value):return hashlib.sha256(value.encode()).hexdigest()

def verify_protocol():
    protocol=json.loads((ROOT/'semantic/fit-protocol.json').read_text())
    if protocol['feature_version']!=FEATURE_VERSION or protocol['revision']!=REVISION or protocol['split_sha256']!=SPLIT_SHA:
        raise ValueError('Frozen protocol identity mismatch')
    if protocol['limits']!={'wall_seconds':WALL_SECONDS,'rss_kib':RSS_KIB,'artifact_bytes':ARTIFACT_BYTES}:
        raise ValueError('Frozen resource contract mismatch')
    for name,expected in protocol['code_sha256'].items():
        if digest(ROOT/name)!=expected:raise ValueError('Reviewed source digest mismatch')
    for name,expected in protocol['fit_packages'].items():
        if importlib.metadata.version(name)!=expected:raise ValueError('Fit dependency pin mismatch')
    return protocol

class Rules:
    def __enter__(self):
        self.child=subprocess.Popen(['node',str(ROOT/'semantic/rules_bridge.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        return self
    def flags(self,row):
        self.child.stdin.write(canonical(adapt(row,row['_subset'],exclude_final=True))+'\n');self.child.stdin.flush()
        result=json.loads(self.child.stdout.readline())
        if not isinstance(result,list) or any(type(i) is not int for i in result):raise ValueError('Rules baseline failed')
        return set(result)
    def __exit__(self,*args):
        self.child.stdin.close()
        try:self.child.wait(timeout=2)
        except subprocess.TimeoutExpired:self.child.kill();self.child.wait()
        self.child.stdout.close()

def prepare(rows,tokenizer,rules):
    samples=[]
    for row in rows:
        if row['_split'] not in ('train','validation'):raise ValueError('TEST cannot enter preparation')
        last=max(i for i,m in enumerate(row['messages']) if m['role']=='assistant')
        flags=rules.flags(row) if row['_split']=='validation' else set()
        seen=set()
        for key,label in sorted(row['step_labels'].items(),key=lambda pair:int(pair[0])):
            index=int(key)
            if index in seen or not 0<=index<len(row['messages']) or row['messages'][index]['role']!='assistant' or type(label) is not int or label not in (-1,0,1):
                raise ValueError('Invalid supervised target')
            seen.add(index)
            if index>=last:continue
            prepared,audit=prepare_input(row,index)
            streams,token_audit=tokenize(prepared,tokenizer)
            audit['tokens']=token_audit
            samples.append({'split':row['_split'],'group':row['_group'],'subset':row['_subset'],'label':label,
                            'query_index':row['query_index'],'sample_index':row['sample_index'],'message_index':index,
                            'rule':index in flags,'support_reason':token_audit['support_reason'],'audit':audit,
                            'input_sha256':sha(canonical(prepared)),'streams':streams})
            if len(samples)>MAX_TARGETS:raise ValueError('Target ceiling exceeded')
    return samples

def cache_key(sample,identity):
    if sample['split'] not in ('train','validation'):raise ValueError('TEST cache forbidden')
    return sha(canonical({'encoder_revision':REVISION,'feature_version':FEATURE_VERSION,
                          'feature_code_sha256':identity['feature_code_sha256'],'source_sha256':identity['source_sha256'],
                          'split_sha256':SPLIT_SHA,'assignment':sample['split'],'input_sha256':sample['input_sha256'],
                          'token_ids_sha256':sha(canonical(sample['streams']))}))

def encode_samples(samples,encoder,identity):
    """Per-run memory-only cache. No disk deserialization, labels or cross-split reuse."""
    import numpy as np
    matrix=np.zeros((len(samples),768),dtype=np.float32);cache={};pending=[];hits=0;encoded_streams=0
    def flush():
        nonlocal encoded_streams
        if not pending:return
        streams=[s['streams'][part] for _,s,_ in pending for part in ('context','action')]
        pairs=encoder.encode(streams).reshape(-1,768);encoded_streams+=len(streams)
        for (i,s,key),pair in zip(pending,pairs):
            if not np.isfinite(pair).all():raise ValueError('Nonfinite cached embedding')
            matrix[i]=pair;cache[key]=pair.copy()
        if len(cache)*768*4>CACHE_BYTES:raise ValueError('Embedding cache ceiling')
        pending.clear()
    for i,sample in enumerate(samples):
        if sample['split'] not in ('train','validation'):raise ValueError('TEST cannot enter encoding')
        if sample['support_reason'] is not None:continue
        key=cache_key(sample,identity)
        if key in cache:matrix[i]=cache[key];hits+=1
        else:
            pending.append((i,sample,key))
            if len(pending)==4:flush()
    flush()
    return matrix,{'entries':len(cache),'bytes':len(cache)*768*4,'hits':hits,'persistent':False,'encoded_streams':encoded_streams,
                   'key_contract':'revision + feature version/code + source hashes + split hash/assignment + prepared input hash + token IDs hash'}

def coverage(samples,groups_by_split,groups_by_split_subset):
    def measure(records,groups):
        supported=[r for r in records if r['support_reason'] is None]
        return {'steps':len(records),'task_groups':len(groups),'task_groups_with_targets':len({r['group'] for r in records}),
                'supported_steps':len(supported),'unsupported_steps':len(records)-len(supported),
                'unsupported_reasons':dict(collections.Counter(r['support_reason'] for r in records if r['support_reason'] is not None)),
                'truncated_steps':sum(any(v['removed'] for v in r['audit']['characters'].values()) or any(v['removed'] for v in r['audit']['tokens']['fields'].values()) or any(v['removed'] for c in r['audit']['tokens']['calls'] for v in c.values()) or any(v['removed'] for c in r['audit']['calls'] for v in c.values()) or any(f['characters_before']>f['characters_retained'] for previous in r['audit']['previous_fields'] for f in previous.get('fields',[])) for r in records),
                'unknown_tokens_before':sum(sum(v['unknown_before'] for v in r['audit']['tokens']['fields'].values())+sum(v['unknown_before'] for c in r['audit']['tokens']['calls'] for v in c.values()) for r in records)}
    result={}
    for split in ('train','validation'):
        records=[r for r in samples if r['split']==split];groups=groups_by_split[split]
        result[split]={'all':measure(records,groups),'by_label':{str(label):measure([r for r in records if r['label']==label],groups) for label in (-1,0,1)},
                       'by_subset':{subset:measure([r for r in records if r['subset']==subset],groups) for subset,groups in groups_by_split_subset[split].items()}}
    return result

def evaluate(validation,groups):
    gate=choose_threshold([{k:r[k] for k in ('split','group','subset','label','rule','score')} for r in validation],set(groups))
    metrics=[gate['rules'],gate['never_flag']]+[c[k] for c in gate['candidates'] for k in ('model','combined')]
    for m in metrics:
        for group in groups:m['per_task_confusion'].setdefault(group,dict.fromkeys(('tp','fp','fn','tn'),0))
        m['task_groups']=len(groups)
        m['per_task_metrics']={}
        for group,c in m['per_task_confusion'].items():
            tp,fp,fn=c['tp'],c['fp'],c['fn']
            m['per_task_metrics'][group]={'precision':tp/(tp+fp) if tp+fp else 0,'recall':tp/(tp+fn) if tp+fn else 0,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0}
    return gate

def positional_evidence(validation):
    # No text, arguments, names, call IDs, prompts, answers or traces are exported.
    return [{**{k:r[k] for k in ('split','subset','group','query_index','sample_index','message_index','label','rule','score','support_reason','audit')},
             'text_redacted':True,'model_flags':{str(t):r['score'] is not None and r['score']>t and abs(r['score']-t)>1e-6 for t in THRESHOLDS}} for r in validation]

def fit_head(matrix,samples,estimator_factory=None):
    indices=[i for i,s in enumerate(samples) if s['split']=='train' and s['support_reason'] is None]
    if any(s['split'] not in ('train','validation') for s in samples):raise ValueError('TEST cannot enter fit')
    if {samples[i]['label'] for i in indices}!={-1,0,1}:raise ValueError('Supported TRAIN must contain all classes')
    if estimator_factory is None:
        from sklearn.linear_model import LogisticRegression
        estimator_factory=LogisticRegression
    model=estimator_factory(C=1.0,solver='lbfgs',max_iter=500,class_weight=None,random_state=42,tol=1e-4)
    model.fit(matrix[indices],[samples[i]['label'] for i in indices])  # Exactly one fit, never a retry.
    return model


def execute_fit(data,directory,stage):
    protocol=verify_protocol()
    rows,provenance=load_verified(data,ROOT/'research/split.json',SPLIT_SHA)
    from semantic.runtime import Encoder,head_probabilities
    encoder=Encoder(directory)
    with Rules() as rules:samples=prepare(rows,encoder.tokenizer,rules)
    del rows
    if dict(collections.Counter(s['split'] for s in samples))!={'train':4824,'validation':1390}:raise ValueError('Frozen target counts differ')
    report={'status':'prepared','artifact_ready':False,'feature_version':FEATURE_VERSION,'protocol_sha256':digest(ROOT/'semantic/fit-protocol.json'),
            'provenance':provenance,'coverage':coverage(samples,provenance['groups_by_split'],provenance['groups_by_split_subset']),'benchmark_rows_encoded':0,'head_fits':0}
    # No diagnostic report contains the source inputs or tokenizer IDs.
    (stage/'coverage.json').write_text(canonical(report))
    identity={'feature_code_sha256':sha(canonical({name:protocol['code_sha256'][name] for name in ('semantic/features.py','semantic/contract.py','semantic/runtime.py')})),'source_sha256':provenance['source_sha256']}
    encode_started=time.monotonic();matrix,cache=encode_samples(samples,encoder,identity)
    report['encoding_seconds']=time.monotonic()-encode_started
    report['benchmark_rows_encoded']=sum(s['support_reason'] is None for s in samples)
    report['cache']=cache
    import numpy as np
    train_indices=[i for i,s in enumerate(samples) if s['split']=='train' and s['support_reason'] is None]
    fit_started=time.monotonic()
    model=fit_head(matrix,samples)
    report['head_fits']=1;report['fit_seconds']=time.monotonic()-fit_started
    if model.classes_.tolist()!=[-1,0,1] or int(model.n_iter_.max())>=500:raise ValueError('Class/convergence contract failed')
    head={'classes':[-1,0,1],'coefficients':model.coef_.tolist(),'intercept':model.intercept_.tolist(),'feature_version':FEATURE_VERSION,'encoder_revision':REVISION}
    head=json.loads(canonical(head))  # Parity uses the actual JSON round trip.
    supported=[i for i,s in enumerate(samples) if s['split']=='validation' and s['support_reason'] is None]
    max_error=0.0
    if supported:
        expected=model.predict_proba(matrix[supported]);actual=head_probabilities(matrix[supported],head)
        max_error=float(np.max(np.abs(expected-actual)))
        if max_error>1e-6:raise ValueError('Learned JSON head score parity')
        for threshold in THRESHOLDS:
            ref=(expected[:,0]>threshold)&(np.abs(expected[:,0]-threshold)>1e-6)
            local=(actual[:,0]>threshold)&(np.abs(actual[:,0]-threshold)>1e-6)
            if not np.array_equal(ref,local):raise ValueError('Learned head decision parity')
        scores=dict(zip(supported,map(float,actual[:,0])))
    else:scores={}
    for i,sample in enumerate(samples):sample['score']=scores.get(i)
    validation=[s for s in samples if s['split']=='validation'];gate=evaluate(validation,provenance['validation_groups'])
    report.update(status='completed',gate=gate,score_max_absolute_error=max_error,thresholds=list(THRESHOLDS),
                  evidence=positional_evidence(validation),training_coverage_evidence=positional_evidence([s for s in samples if s['split']=='train']),quality_claim='Development validation only; TEST is spent and excluded.')
    if gate['selected_threshold'] is not None:
        head['threshold']=gate['selected_threshold'];head['provenance']=provenance
        bundle=stage/'candidate';bundle.mkdir()
        (bundle/'head.json').write_text(canonical(head))
        for name in encoder.sizes:
            target=bundle/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(directory/name,target)
        # Local provenance; no remote fetch or app activation.
        shutil.copytree(ROOT/'semantic/notices',bundle/'notices')
        shutil.copyfile(ROOT/'semantic/fit-protocol.json',bundle/'fit-protocol.json')
        shutil.copyfile(ROOT/'semantic/runtime-lock.json',bundle/'runtime-lock.json')
        files={str(p.relative_to(bundle)):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in bundle.rglob('*') if p.is_file()}
        total=sum(f['bytes'] for f in files.values())
        if total>ARTIFACT_BYTES:raise ValueError('Model artifact ceiling exceeded')
        report.update(artifact_ready=True,artifact_bytes=total,artifact_files=files)
    serialized=canonical(report)
    if len(serialized.encode())>REPORT_BYTES:raise ValueError('Report ceiling exceeded')
    (stage/'report.json').write_text(serialized)


def resources_ok(resource):
    def within(value,cap):return type(value) in (int,float) and math.isfinite(value) and 0<=value<=cap
    return (type(resource.get('exit_code')) is int and resource['exit_code']==0 and resource.get('stop_reason','missing') is None
            and within(resource.get('elapsed_seconds'),WALL_SECONDS) and within(resource.get('sampled_peak_group_rss_kib'),RSS_KIB))

def publish(stage,output,resource,started):
    """Only bounded success and verified eligible bundle can be atomically published."""
    if output.exists():raise ValueError('Output must be new')
    if not resources_ok(resource):raise ValueError('Final resource gate failed')
    path=stage/'report.json'
    if path.stat().st_size>REPORT_BYTES:raise ValueError('Report ceiling')
    report=json.loads(path.read_text())
    if report.get('status')!='completed' or report.get('head_fits')!=1:raise ValueError('Completed single fit required')
    if report.get('artifact_ready'):
        gate=report['gate'];selected=gate['selected_threshold']
        recomputed=evaluate(report['evidence'],report['provenance']['validation_groups'])
        if gate!=recomputed:raise ValueError('Final validation gate mismatch')
        if not any(c['threshold']==selected and c['eligible'] for c in gate['candidates']):raise ValueError('FP gate failed')
        bundle=stage/'candidate';inventory={str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file()}
        if inventory!=set(report['artifact_files']):raise ValueError('Artifact inventory mismatch')
        from semantic.contract import WEIGHTS
        locked=json.loads((ROOT/'semantic/runtime-lock.json').read_text())['files']
        required={**locked,'onnx/model.onnx':{'bytes':WEIGHTS['onnx/model.onnx'][0],'sha256':WEIGHTS['onnx/model.onnx'][1]}}
        for name,pin in required.items():
            if report['artifact_files'].get(name)!={'bytes':pin['bytes'],'sha256':pin['sha256']}:raise ValueError('Pinned artifact mismatch')
        if not {'head.json','notices/NOTICE.txt','notices/LICENSE-2.0.txt','notices/all-MiniLM-L6-v2-model-card.md','fit-protocol.json','runtime-lock.json'}<=inventory:
            raise ValueError('Incomplete artifact')
        head=json.loads((bundle/'head.json').read_text())
        if head.get('threshold')!=selected or head.get('feature_version')!=FEATURE_VERSION or head.get('encoder_revision')!=REVISION:
            raise ValueError('Final head contract mismatch')
        total=0
        for name,entry in report['artifact_files'].items():
            path=bundle/name
            if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file() or path.stat().st_size!=entry['bytes'] or digest(path)!=entry['sha256']:
                raise ValueError('Artifact source mismatch')
            total+=entry['bytes']
        if total!=report['artifact_bytes'] or total>ARTIFACT_BYTES:raise ValueError('Artifact ceiling')
    else:
        if (stage/'candidate').exists():shutil.rmtree(stage/'candidate')
    elapsed=time.monotonic()-started
    if not 0<=elapsed<=WALL_SECONDS:raise ValueError('Final publication wall-time failed')
    report['resource']={**resource,'end_to_end_seconds':elapsed}
    encoded=canonical(report)
    if len(encoded.encode())>REPORT_BYTES:raise ValueError('Final report ceiling')
    (stage/'report.json').write_text(encoded)
    (stage/'coverage.json').unlink(missing_ok=True)
    if time.monotonic()-started>WALL_SECONDS:raise ValueError('Final publication wall-time failed')
    stage.rename(output)  # Same filesystem; no unbounded model copy outside supervisor.
    if time.monotonic()-started>WALL_SECONDS:
        shutil.rmtree(output)
        raise ValueError('Final publication wall-time failed')
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True,type=Path);parser.add_argument('--model-dir',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--execute-reviewed-fit',action='store_true')
    parser.add_argument('--_worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if not args.execute_reviewed_fit:parser.error('Parent execution approval required before --execute-reviewed-fit')
    if args._worker:
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',CUDA_VISIBLE_DEVICES='',TOKENIZERS_PARALLELISM='false')
        try:
            with patch.object(socket.socket,'connect',side_effect=RuntimeError('Offline only')):
                execute_fit(args.data,args.model_dir,args.output)
        except Exception as error:
            # No raw source, tracebacks or third-party exception content in logs.
            print(canonical({'status':'failed','error_type':type(error).__name__}),file=sys.stderr)
            raise SystemExit(1)
        return
    started=time.monotonic()
    if args.output.exists():parser.error('Output must be new; no overwrite or retry')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    marker=args.output.with_name(args.output.name+'.attempt.json')
    with marker.open('x') as stream:stream.write(canonical({'protocol_sha256':digest(ROOT/'semantic/fit-protocol.json'),'status':'attempt-started-no-automatic-retry'}))
    with tempfile.TemporaryDirectory(prefix='.semantic-fit-',dir=args.output.parent) as temporary:
        stage=Path(temporary)/'result';stage.mkdir(mode=0o700)
        resource=run_bounded([sys.executable,str(Path(__file__).resolve()),'--_worker','--execute-reviewed-fit','--data',str(args.data.resolve()),'--model-dir',str(args.model_dir.resolve()),'--output',str(stage)],seconds=max(.001,WALL_SECONDS-(time.monotonic()-started)))
        try:report=publish(stage,args.output,resource,started)
        except (ValueError,OSError,KeyError) as error:
            marker.write_text(canonical({'status':'failed-no-artifact','resource':resource,'error_type':type(error).__name__}))
            raise SystemExit(1)
    marker.write_text(canonical({'status':'completed','artifact_ready':report['artifact_ready'],'resource':report['resource']}))
    print(canonical({'status':report['status'],'artifact_ready':report['artifact_ready']}))

if __name__=='__main__':main()
