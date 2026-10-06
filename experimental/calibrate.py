"""Review-only calibration driver. No execution authorized until parent review.

Public CLI verifies immutable data/splits inside a 60s/512MiB child. Exactly one
TRAIN fit is possible per invocation. TEST messages never enter preparation.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from bounded import run_bounded
from contract import make_envelope, encode, artifact
from policy import choose_threshold, THRESHOLDS
from adapter import adapt, feature

ROOT=Path(__file__).resolve().parents[1]
ADAPTER_SHA='ed0c1200a9e2688e20ad59398ec9fc27d13e85cf1fdc5469791f4ce6107da457'
SPLIT_SHA='7a7d222f87069b840eccab45abb3d7e35da51fc2b11e62a18d89a9a34eab7524'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def load_verified(data, split_path, split_sha, *, source_groups=200, independent_groups=189, attempts=5):
    """Hash first, audit all routing metadata, retain only TRAIN/validation rows.

Question hashes are used solely to verify independent task grouping, including
cross-split duplicates. TEST labels/messages are never inspected, adapted, featurized or scored.
Synthetic tests inject their own immutable manifest; public CLI cannot do so.
"""
    split_bytes=Path(split_path).read_bytes()
    if hashlib.sha256(split_bytes).hexdigest()!=split_sha:raise ValueError('Frozen split hash mismatch')
    split=json.loads(split_bytes)
    groups=split['groups'];sources=split['source_sha256']
    if len(groups)!=source_groups or set(groups.values())!={'train','validation','test'}:raise ValueError('Invalid frozen memberships')
    if any(Path(name).name!=name or not name.endswith('.jsonl') for name in sources):raise ValueError('Invalid source name')
    if {p.name for p in Path(data).glob('*.jsonl')}!=set(sources):raise ValueError('Unexpected source file inventory')
    for name,expected in sources.items():
        if digest(Path(data)/name)!=expected:raise ValueError('Source hash mismatch')
    parent={key:key for key in groups};questions={};seen=collections.defaultdict(set);rows=[]
    def root(key):
        while parent[key]!=key:key=parent[key]
        return key
    split_runs=collections.Counter()
    for name in sorted(sources):
        consumed_hash=hashlib.sha256()
        with (Path(data)/name).open('rb') as source:
            for line in source:
                consumed_hash.update(line)
                row=json.loads(line)
                if type(row.get('query_index')) is not int or type(row.get('sample_index')) is not int:raise ValueError('Invalid routing IDs')
                group=f'{Path(name).stem}:{row["query_index"]}'
                if group not in groups or row['sample_index'] in seen[group]:raise ValueError('Unknown group or duplicate attempt')
                if not 0<=row['sample_index']<attempts:raise ValueError('Invalid attempt index')
                seen[group].add(row['sample_index']);split_runs[groups[group]]+=1
                question_hash=sha(' '.join(row['question'].lower().split()))
                if question_hash in questions:parent[root(group)]=root(questions[question_hash])
                questions[question_hash]=group
                if groups[group]=='test':continue  # Before labels, adapter, features, rules or inference.
                row['_group']=group;row['_split']=groups[group];row['_subset']=Path(name).stem
                rows.append(row)
        if consumed_hash.hexdigest()!=sources[name]:raise ValueError('Source changed during routing')
    if set(seen)!=set(groups) or any(len(values)!=attempts for values in seen.values()):raise ValueError('Incomplete task/attempt coverage')
    if len({root(key) for key in groups})!=independent_groups:raise ValueError('Independent group count mismatch')
    roots=collections.defaultdict(set)
    for key,assignment in groups.items():roots[root(key)].add(assignment)
    if any(len(values)!=1 for values in roots.values()):raise ValueError('Cross-split duplicate tasks')
    for row in rows:row['_group']=root(row['_group'])
    return rows, {'split_sha256':split_sha,'source_sha256':sources,'routing_runs':dict(split_runs),
                  'validation_groups':sorted({root(k) for k,v in groups.items() if v=='validation'})}

class Bridge:
    def __enter__(self):
        self.process=subprocess.Popen(['node',str(ROOT/'experimental/calibration_bridge.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        return self
    def ask(self, value):
        self.process.stdin.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n');self.process.stdin.flush()
        response=self.process.stdout.readline()
        if not response:raise RuntimeError('Calibration bridge exited')
        result=json.loads(response)
        if 'error' in result:raise RuntimeError(result['error'])
        return result
    def __exit__(self,*_):
        self.process.stdin.close()
        try:self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.process.stdout.close()

def prepare(rows, bridge):
    samples=[]
    for row in rows:
        if row['_split'] not in ('train','validation'):raise ValueError('TEST cannot enter feature preparation')
        last=max(i for i,m in enumerate(row['messages']) if m['role']=='assistant')
        targets=[]
        for key,label in row['step_labels'].items():
            index=int(key)
            if not 0<=index<len(row['messages']) or row['messages'][index]['role']!='assistant' or type(label) is not int or label not in (-1,0,1):raise ValueError('Invalid supervised target')
            if index<last:targets.append((index,label))
        try:envelope_json=encode(make_envelope(row))
        except (ValueError,TypeError,KeyError):envelope_json=None
        result=bridge.ask({'envelopeJSON':envelope_json,'indices':[i for i,_ in targets],
                           'rule_run':adapt(row,row['_subset'],exclude_final=True) if row['_split']=='validation' else None})
        for index,label in targets:
            text=feature(row,index)
            if result['compatible'] and result['hashes'].get(str(index))!=sha(text):raise ValueError('Actual Python/browser feature parity failed')
            reason='incompatible-envelope' if not result['compatible'] else 'unsupported-unicode' if not text.isascii() else None
            samples.append({'split':row['_split'],'group':row['_group'],'subset':row['_subset'],'label':label,
                            'rule':index in result['rule_indices'],'text':text,'support_reason':reason})
    return samples

def coverage(samples):
    """Retain every target; mixed groups appear in both support group counts."""
    def measure(records):
        supported=[r for r in records if r['support_reason'] is None]
        unsupported=[r for r in records if r['support_reason'] is not None]
        return {'steps':len(records),'task_groups':len({r['group'] for r in records}),
                'supported_steps':len(supported),'unsupported_steps':len(unsupported),
                'supported_task_groups':len({r['group'] for r in supported}),
                'unsupported_task_groups':len({r['group'] for r in unsupported}),
                'unsupported_reasons':dict(collections.Counter(r['support_reason'] for r in unsupported))}
    result={}
    for split in ('train','validation'):
        records=[r for r in samples if r['split']==split]
        result[split]={'all':measure(records),'by_label':{str(label):measure([r for r in records if r['label']==label]) for label in (-1,0,1)},
                       'by_subset':{subset:{'all':measure([r for r in records if r['subset']==subset]),
                                           'by_label':{str(label):measure([r for r in records if r['subset']==subset and r['label']==label]) for label in (-1,0,1)}} for subset in sorted({r['subset'] for r in records})}}
    return result

def execute_fit(data, stage):
    # Called only in the explicitly reviewed supervised child, never during tests.
    if digest(ROOT/'research/adapter.py')!=ADAPTER_SHA:raise ValueError('Frozen feature extractor changed')
    rows,provenance=load_verified(data,ROOT/'research/split.json',SPLIT_SHA)
    with Bridge() as bridge:samples=prepare(rows,bridge)
    del rows
    input_coverage=coverage(samples)
    if {k:v['all']['steps'] for k,v in input_coverage.items()}!={'train':4824,'validation':1390}:raise ValueError('Frozen target counts differ')
    # Persist non-sensitive coverage before importing the ML stack. A failed fit
    # may keep this diagnostic report but can never publish a candidate model.
    Path(stage,'coverage.json').write_text(json.dumps(input_coverage,indent=2))
    import numpy as np
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    if sklearn.__version__!='1.8.0' or np.__version__!='2.3.5':raise ValueError('Pinned research dependencies required')
    train=[r for r in samples if r['split']=='train'];validation=[r for r in samples if r['split']=='validation']
    vectorizer=TfidfVectorizer(max_features=20000,ngram_range=(1,2),min_df=2,sublinear_tf=True)
    started=time.monotonic()
    x=vectorizer.fit_transform(r['text'] for r in train)
    model=LogisticRegression(C=1.0,max_iter=500,solver='lbfgs',random_state=42)
    model.fit(x,[r['label'] for r in train])  # The single classifier fit.
    if model.n_iter_.max()>=500 or model.classes_.tolist()!=[-1,0,1]:raise ValueError('Fit failed convergence/class contract')
    fit_seconds=time.monotonic()-started
    vx=vectorizer.transform(r['text'] if r['support_reason'] is None else '' for r in validation)
    for records,matrix in [(train,x),(validation,vx)]:
        for record,nonzero in zip(records,matrix.getnnz(axis=1)):
            if record['support_reason'] is None and not nonzero:record['support_reason']='no-known-features'
    supported_indices=[i for i,r in enumerate(validation) if r['support_reason'] is None]
    probabilities=[None]*len(validation)
    if supported_indices:
        for i,probability in zip(supported_indices,model.predict_proba(vx[supported_indices])):probabilities[i]=probability
    for record,probability in zip(validation,probabilities):record['score']=float(probability[0]) if probability is not None else None
    gate_rows=[{key:r[key] for key in ('split','group','subset','label','rule','score')} for r in validation]
    gate=choose_threshold(gate_rows,set(provenance['validation_groups']))
    report={'status':'completed','interpretation':gate['interpretation'],'provenance':provenance,
            'input_coverage':input_coverage,'model_coverage':coverage(samples),'gate':gate,
            'fit_seconds':fit_seconds,'thresholds':list(THRESHOLDS),'artifact_ready':False,
            'never_flag':{'flags':0,'fp':0,'tp':0,'fn':sum(r['label']==-1 for r in validation),'tn':sum(r['label']!=-1 for r in validation),'precision':0,'recall':0,'f1':0},
            'feature_extractor_sha256':ADAPTER_SHA,
            'code_sha256':{str(p.relative_to(ROOT)):digest(p) for folder in ['experimental','web'] for p in sorted((ROOT/folder).glob('*')) if p.is_file()}}
    selected=gate['selected_threshold']
    if selected is not None:
        try:
            payload=artifact(vectorizer.get_feature_names_out().tolist(),vectorizer.idf_.tolist(),model.coef_.tolist(),model.intercept_.tolist(),selected,
                             {'kind':'train-validation','source_hashes':[provenance['source_sha256'][k] for k in sorted(provenance['source_sha256'])],'split_sha256':SPLIT_SHA})
            encoded=encode(payload)
            maximum_error=0
            with Bridge() as bridge:
                bridge.ask({'artifactJSON':encoded})
                for record,expected in zip(validation,probabilities):
                    if record['support_reason'] is not None:continue
                    actual=bridge.ask({'text':record['text']})
                    error=max(abs(a-float(b)) for a,b in zip(actual['scores'],expected))
                    maximum_error=max(maximum_error,error)
                    if error>1e-6 or actual['suggestion']!=(record['score']>selected and abs(record['score']-selected)>1e-6):raise ValueError('Actual artifact score/decision parity failed')
            report.update(artifact_ready=True,artifact_bytes=len(encoded.encode()),artifact_sha256=sha(encoded),artifact_score_max_error=maximum_error)
            Path(stage,'candidate.json').write_text(encoded)
        except (ValueError,TypeError,RuntimeError):report['artifact_blocker']='Artifact contract or actual-weight parity failed; no export, retry or relaxation.'
    Path(stage,'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))


def publish(stage, output, resource):
    """Only successful supervisor + report + gates can copy candidate bytes."""
    output=Path(output);output.mkdir(mode=0o700,exist_ok=False)
    report_path=Path(stage,'report.json')
    success=(resource['exit_code']==0 and resource['stop_reason'] is None
             and 0<=resource['elapsed_seconds']<=60 and 0<=resource['sampled_peak_group_rss_kib']<=512*1024)
    report=json.loads(report_path.read_text()) if success and report_path.exists() else {'status':'failed','artifact_ready':False}
    if report.get('status')!='completed':success=False
    report['resource']=resource
    ready=success and report.get('artifact_ready') is True
    if ready:
        candidates=report['gate']['candidates'];selected=report['gate']['selected_threshold']
        ready=any(c['threshold']==selected and c['eligible'] for c in candidates)
        candidate=Path(stage,'candidate.json')
        ready=ready and candidate.is_file() and candidate.stat().st_size<=2*1024*1024 and digest(candidate)==report.get('artifact_sha256')
    report['artifact_ready']=bool(ready)
    if ready:shutil.copyfile(candidate,output/'model.json')
    if not success and Path(stage,'coverage.json').exists():
        report['input_coverage']=json.loads(Path(stage,'coverage.json').read_text())
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--execute-reviewed-fit',action='store_true',help='Only use after parent approves this driver and frozen plan')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:
        execute_fit(args.data,args.output);return
    if not args.execute_reviewed_fit:parser.error('No fit authorized by default; review is required before --execute-reviewed-fit')
    if args.output.exists():parser.error('Output must be a new directory; previous results are immutable')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.calibration-stage-',dir=args.output.parent) as stage:
        resource=run_bounded([sys.executable,str(Path(__file__).resolve()),'--worker','--data',str(args.data.resolve()),'--output',stage])
        report=publish(stage,args.output,resource)
    print(json.dumps({'status':report['status'],'artifact_ready':report['artifact_ready'],'output':str(args.output)}))
    if report['status']!='completed':raise SystemExit(1)

if __name__=='__main__':main()
