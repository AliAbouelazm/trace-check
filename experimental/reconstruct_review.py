"""One authorized deterministic build reconstruction, not automatic promotion.

Uses the archived TRAIN fit; exports only manual-review JSON at fixed cutoff .70.
No TEST features, searches, retries, semantic fits or automatic flag activation.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import warnings
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
FROZEN=Path('/tmp/tracecheck-tfidf-frozen')
FROZEN_COMMIT='c51598b319cdefcad893860f1c1ccd5e82a4bbc9'
RECEIPT_SHA='aa8a0252474e79dd90932e4db76603f817e7b3d6f8a122bf5c5f99ed03ef9c9f'
MAX_BYTES=2*1024*1024

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def worker(data,stage):
    if subprocess.check_output(['git','-C',str(FROZEN),'rev-parse','HEAD'],text=True).strip()!=FROZEN_COMMIT:raise ValueError('Archived checkout mismatch')
    sys.path.insert(0,str(FROZEN/'experimental'))
    import calibrate as old
    receipt_path=ROOT/'experimental/results/calibration-2026-10-06.json'
    if digest(receipt_path)!=RECEIPT_SHA:raise ValueError('Archived receipt mismatch')
    receipt=json.loads(receipt_path.read_text())
    for name in ('experimental/calibrate.py','experimental/contract.py','experimental/policy.py','experimental/calibration_bridge.mjs','web/experimental.js','web/core.js'):
        if digest(FROZEN/name)!=receipt['code_sha256'][name]:raise ValueError('Archived code mismatch')
    if digest(FROZEN/'research/adapter.py')!=old.ADAPTER_SHA:raise ValueError('Feature extractor mismatch')
    import importlib.metadata
    pins={'numpy':'2.3.5','scikit-learn':'1.8.0','scipy':'1.17.0','joblib':'1.5.3','threadpoolctl':'3.6.0'}
    if any(importlib.metadata.version(k)!=v for k,v in pins.items()):raise ValueError('Build package pins mismatch')
    rows,provenance=old.load_verified(data,FROZEN/'research/split.json',old.SPLIT_SHA)
    positions=[]
    for row in rows:
        last=max(i for i,m in enumerate(row['messages']) if m['role']=='assistant')
        positions.extend({'query_index':row['query_index'],'sample_index':row['sample_index'],'message_index':int(k)} for k in row['step_labels'] if int(k)<last)
    with old.Bridge() as bridge:samples=old.prepare(rows,bridge)
    del rows
    if len(samples)!=len(positions):raise ValueError('Position mapping mismatch')
    for record,position in zip(samples,positions):record.update(position)
    input_coverage=old.coverage(samples)
    if input_coverage!=receipt['input_coverage']:raise ValueError('Archived input coverage mismatch')
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.exceptions import ConvergenceWarning
    train=[r for r in samples if r['split']=='train'];validation=[r for r in samples if r['split']=='validation']
    if len(train)!=4824 or len(validation)!=1390:raise ValueError('Frozen target counts mismatch')
    vectorizer=TfidfVectorizer(max_features=20000,ngram_range=(1,2),min_df=2,sublinear_tf=True)
    started=time.monotonic();x=vectorizer.fit_transform(r['text'] for r in train)
    model=LogisticRegression(C=1.0,max_iter=500,solver='lbfgs',random_state=42)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        model.fit(x,[r['label'] for r in train])  # The one separately authorized additional fit.
    fit_seconds=time.monotonic()-started
    if model.n_iter_.max()>=500 or model.classes_.tolist()!=[-1,0,1]:raise ValueError('Convergence/class failure')
    from contract import artifact,encode
    payload=artifact(vectorizer.get_feature_names_out().tolist(),vectorizer.idf_.tolist(),model.coef_.tolist(),model.intercept_.tolist(),.70,
                     {'kind':'train-validation','source_hashes':[provenance['source_sha256'][k] for k in sorted(provenance['source_sha256'])],'split_sha256':old.SPLIT_SHA})
    encoded=encode(payload)
    # Canonical JS serialization makes a browser JSON-module round-trip hash
    # identical to the bounded file bytes. Values are parsed as data, never eval.
    encoded=subprocess.check_output(['node','-e',"let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(JSON.parse(s))));"],input=encoded,text=True)
    if len(encoded.encode())>MAX_BYTES:raise ValueError('Artifact exceeds 2 MiB')
    (stage/'checkpoint.json').write_text(encoded)
    vx=vectorizer.transform(r['text'] if r['support_reason'] is None else '' for r in validation)
    for records,matrix in ((train,x),(validation,vx)):
        for record,nonzero in zip(records,matrix.getnnz(axis=1)):
            if record['support_reason'] is None and not nonzero:record['support_reason']='no-known-features'
    if old.coverage(samples)!=receipt['model_coverage']:raise ValueError('Archived model coverage mismatch')
    supported=[i for i,r in enumerate(validation) if r['support_reason'] is None]
    probabilities=[None]*len(validation)
    for i,p in zip(supported,model.predict_proba(vx[supported])):probabilities[i]=p
    for r,p in zip(validation,probabilities):r['score']=float(p[0]) if p is not None else None
    compared=old.choose_threshold([{k:r[k] for k in ('split','group','subset','label','rule','score')} for r in validation],set(provenance['validation_groups']))
    # Recompute the six *archived* policies solely as reconstruction checks.
    # This does not select or alter the independently fixed manual-review .70.
    if compared!=receipt['gate']:raise ValueError('Archived aggregate/per-task comparison mismatch')
    if compared['selected_threshold'] is not None:raise ValueError('Historical automatic gate state changed')
    max_error=0.0
    with old.Bridge() as bridge:
        bridge.ask({'artifactJSON':encoded})
        for record,expected in zip(validation,probabilities):
            if expected is None:continue
            actual=bridge.ask({'text':record['text']})
            error=max(abs(a-float(b)) for a,b in zip(actual['scores'],expected));max_error=max(max_error,error)
            if error>1e-6 or actual['suggestion']!=(record['score']>.70 and abs(record['score']-.70)>1e-6):raise ValueError('Actual-weight JS parity failure')
    predictions=[{**{k:r[k] for k in ('group','subset','query_index','sample_index','message_index','label','rule','support_reason','score')},
                  'feature_sha256':old.sha(r['text']),'scores':None if p is None else list(map(float,p)),
                  'review_suggestion':r['score'] is not None and r['score']>.70 and abs(r['score']-.70)>1e-6} for r,p in zip(validation,probabilities)]
    (stage/'validation-predictions.json').write_text(compact(predictions))
    # Preserve synthetic golden predictions from actual fitted weights for CI
    # and browser checks without distributing any benchmark trace text.
    texts=['assistant I will inspect the configuration and run the tests.',
           'assistant The request failed. I will retry the same command.',
           'assistant Search for the correct document before answering.',
           'assistant Delete the directory and then check the files.',
           'assistant Done. Everything is correct.', 'assistant café “quotes”', '', 'zzunknownwordxx']
    from contract import reference_score
    golden=[{'text':text,'expected':reference_score(json.loads(encoded),text)} for text in texts]
    write(stage/'golden.json',golden)
    report={'status':'reconstructed-for-manual-review-only','additional_fits':1,'original_artifact_retrieved':False,'byte_identity_to_original_unverifiable':True,
            'archived_commit':FROZEN_COMMIT,'archived_receipt_sha256':RECEIPT_SHA,'source_provenance':provenance,'packages':pins,
            'fit_seconds':fit_seconds,'iterations':model.n_iter_.tolist(),'fixed_review_cutoff':.70,'automatic_promotion_eligible':False,
            'all_archived_aggregate_and_per_task_counts_match':True,'matching_counts_prove_original_per_step_identity':False,
            'actual_python_js_score_max_error':max_error,'actual_python_js_validation_cases':len(supported),
            'artifact_bytes':len(encoded.encode()),'artifact_sha256':hashlib.sha256(encoded.encode()).hexdigest(),
            'prediction_bytes':(stage/'validation-predictions.json').stat().st_size,'prediction_sha256':digest(stage/'validation-predictions.json'),
            'input_coverage':input_coverage,'model_coverage':old.coverage(samples),'archived_policy_comparison':compared,
            'test_encoded_or_scored':False,'no_hyperparameter_or_threshold_search':True,'source_code_sha256':{str(Path(__file__).relative_to(ROOT)):digest(__file__)}}
    write(stage/'report.json',report)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute-approved-reconstruction',action='store_true');parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if not args.execute_approved_reconstruction:parser.error('Separate build reconstruction approval required')
    if args.worker:
        try:
            with patch.object(socket.socket,'connect',side_effect=RuntimeError('Offline build only')):worker(args.data,args.output)
        except Exception as error:
            write(args.output/'failure.json',{'status':'failed-stop-no-retry','error_type':type(error).__name__,'reason':str(error) if isinstance(error,ValueError) else 'See error type; no raw source echoed'})
            raise SystemExit(1)
        return
    started=time.monotonic();args.output.mkdir(parents=True,exist_ok=False)
    stage=args.output/'private-stage';stage.mkdir(mode=0o700)
    from bounded import run_bounded
    resource=run_bounded([sys.executable,str(Path(__file__).resolve()),'--worker','--data',str(args.data.resolve()),'--output',str(stage),'--execute-approved-reconstruction'])
    valid=resource['exit_code']==0 and resource['stop_reason'] is None and 0<=resource['elapsed_seconds']<=60 and 0<=resource['sampled_peak_group_rss_kib']<=512*1024
    receipt={'resource':resource,'published':False,'stage_preserved':True,'automatic_retry':False}
    if valid:
        report=json.loads((stage/'report.json').read_text());model=stage/'checkpoint.json'
        valid=report['additional_fits']==1 and report['all_archived_aggregate_and_per_task_counts_match'] is True and report['automatic_promotion_eligible'] is False and model.stat().st_size<=MAX_BYTES and digest(model)==report['artifact_sha256']
        valid=valid and time.monotonic()-started<=60
        if valid:
            model.rename(args.output/'model.json');receipt['published']=True
            report['resource']=resource;report['end_to_end_seconds']=time.monotonic()-started;write(args.output/'report.json',report)
            if time.monotonic()-started>60:
                (args.output/'model.json').rename(stage/'checkpoint.json');(args.output/'report.json').unlink();receipt['published']=False;valid=False
    write(args.output/'receipt.json',receipt)
    print(compact(receipt))
    if not valid:raise SystemExit(1)

if __name__=='__main__':main()
