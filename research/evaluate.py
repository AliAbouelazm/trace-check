"""Frozen v1 CPU experiment. Custom research split of public test data, not official scores."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from adapter import adapt, feature


def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def normalized(s): return ' '.join(s.lower().split())


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('data', type=Path); parser.add_argument('--output', type=Path, default=Path('research/results.json'))
    args = parser.parse_args(); start = time.perf_counter()
    rows, hashes = [], {}
    for path in sorted(args.data.glob('*.jsonl')):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for line in path.open():
            r = json.loads(line); r['_subset'] = path.stem; r['_group'] = f'{path.stem}:{r["query_index"]}'
            rows.append(r)
    assert len(rows) == 1000, 'Expected frozen official release with 1000 trajectories'
    # Union exact normalized questions across all task IDs, retaining all attempts.
    parent = {r['_group']: r['_group'] for r in rows}
    def root(k):
        while parent[k] != k: k = parent[k]
        return k
    questions = {}
    for r in rows:
        q = digest(normalized(r['question']))
        if q in questions: parent[root(r['_group'])] = root(questions[q])
        questions[q] = r['_group']
    groups = sorted(set(root(k) for k in parent), key=lambda x: digest('trace-check-v1-seed42:' + x))
    n = len(groups); assignment = {g: ('train' if i < int(n*.6) else 'validation' if i < int(n*.8) else 'test') for i, g in enumerate(groups)}
    for r in rows: r['_split'] = assignment[root(r['_group'])]
    seen = collections.defaultdict(set)
    for r in rows: seen[digest(normalized(r['question']))].add(r['_split'])
    assert all(len(v) == 1 for v in seen.values()), 'Task leakage'
    samples = []
    runs = []
    for r in rows:
        runs.append(adapt(r, r['_subset'], exclude_final=True))
        last = max(i for i,m in enumerate(r['messages']) if m['role'] == 'assistant')
        for k, label in r['step_labels'].items():
            i = int(k); assert r['messages'][i]['role'] == 'assistant'
            if i >= last: continue
            samples.append({'row': len(runs)-1, 'index': i, 'label': int(label), 'split': r['_split'], 'group': root(r['_group']), 'subset': r['_subset'], 'text': feature(r,i)})
    # One model, one preset. Validation is reported but never used to retune.
    train = [s for s in samples if s['split']=='train']
    fit_start = time.perf_counter()
    vec = TfidfVectorizer(max_features=20000, ngram_range=(1,2), min_df=2, sublinear_tf=True)
    x = vec.fit_transform(s['text'] for s in train)
    model = LogisticRegression(C=1.0, max_iter=500, solver='lbfgs', random_state=42)
    model.fit(x, [s['label'] for s in train]); fit_seconds = time.perf_counter()-fit_start
    assert model.n_iter_.max() < 500, 'Model did not converge'
    flags = json.loads(subprocess.run(['node','research/rules.mjs'], input=json.dumps(runs), text=True, capture_output=True, check=True).stdout)
    rule_targets = []
    for run, run_flags in zip(runs, flags):
        by_id = {s['id']: s for s in run['steps']}
        calls = {s.get('call_id'): int(s['id'][1:].split('-')[0]) for s in run['steps'] if s['kind']=='tool_call'}
        flagged = set()
        for f in run_flags:
            s = by_id[f['step_id']]
            if s['kind']=='tool_result':
                idx = calls.get(s.get('call_id'))
                if idx is not None: flagged.add(idx)
            elif s['kind'] in ('assistant','tool_call'): flagged.add(int(s['id'][1:].split('-')[0]))
        rule_targets.append(flagged)
    result = {'protocol': 'v1 frozen custom research split of public test-only release; not official benchmark performance', 'source_commit':'0a42606b178a8c69d40c5765dc05c342f921e578','sha256':hashes, 'dataset':{'trajectories':len(rows),'task_groups':len(groups),'labels':sum(len(r['step_labels']) for r in rows),'evaluated_nonfinal_steps':len(samples),'label_counts':dict(collections.Counter(s['label'] for s in samples))}, 'split':{}, 'metrics':{}, 'cost':{}}
    for split in ('train','validation','test'):
        subset = [s for s in samples if s['split']==split]
        result['split'][split] = {'tasks':len(set(s['group'] for s in subset)), 'runs':sum(r['_split']==split for r in rows),'steps':len(subset)}
        if split == 'train': continue
        t = time.perf_counter(); probs = model.predict_proba(vec.transform(s['text'] for s in subset)); infer = time.perf_counter()-t
        y = np.array([s['label'] for s in subset]); negative = probs[:,list(model.classes_).index(-1)] >= .5
        rules = np.array([s['index'] in rule_targets[s['row']] for s in subset])
        metrics = {}
        for name,pred in [('rules',rules),('tfidf_logistic',negative),('never_flag',np.zeros(len(y),dtype=bool))]:
            p,r,f,_ = precision_recall_fscore_support(y==-1,pred,average='binary',zero_division=0)
            def measure(mask):
                z = pred[mask]; truth=(y==-1)[mask]
                return {'steps':int(mask.sum()),'flags':int(z.sum()),'false_positives':int(np.sum(z & ~truth)), 'false_positive_rate':float(np.mean(z[~truth])) if (~truth).any() else None}
            metrics[name] = {'precision':float(p),'recall':float(r),'f1':float(f),'confusion_matrix_tn_fp_fn_tp':confusion_matrix(y==-1,pred,labels=[False,True]).ravel().tolist(),'neutral':measure(y==0),'positive':measure(y==1),'by_subset':{d:measure(np.array([s['subset']==d for s in subset])) for d in sorted(set(s['subset'] for s in subset))}, 'error_examples':[{'run_id':runs[s['row']]['run_id'],'message_index':s['index'],'label':s['label'],'prediction':'flag' if pr else 'no_flag'} for s,pr in zip(subset,pred) if bool(pr)!=(s['label']==-1)][:12]}
        metrics['tfidf_multiclass'] = classification_report(y,model.classes_[probs.argmax(axis=1)],output_dict=True,zero_division=0)
        result['metrics'][split] = metrics
        result['cost'][split+'_inference_seconds'] = infer
    result['cost'].update({'fit_seconds':fit_seconds,'wall_seconds':time.perf_counter()-start,'peak_rss_mb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'features':len(vec.vocabulary_),'sparse_train_matrix_mb':(x.data.nbytes+x.indices.nbytes+x.indptr.nbytes)/1e6,'model_coefficient_mb':model.coef_.nbytes/1e6,'paid_api_calls':0,'gpu_used':False})
    result['limitations'] = ['Last assistant message of every trajectory excluded conservatively, including some genuine intermediate-looking content. No final answer fields or ground truth supplied to model.', 'Model sees current and previous two messages only, max 12000 characters. Structural rules inspect the completed nonfinal run and may use subsequent tool results.', 'Exact normalized question duplicates unioned; semantically similar tasks not fully deduplicated.', 'Neutral exploration is not a mistake. Negative source labels can encode propagation rather than a fresh mistake.', 'Scores are neither calibrated confidence nor causal diagnoses. No model shipped in app pending broader validation.']
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    args.output.with_name('split.json').write_text(json.dumps({'seed':42,'groups':{k:assignment[root(k)] for k in sorted(parent)},'source_sha256':hashes},indent=2)+'\n')
    print(json.dumps({'cost':result['cost'],'test':{k:{m:v[m] for m in ('precision','recall','f1')} for k,v in result['metrics']['test'].items() if 'f1' in v}},indent=2))

if __name__ == '__main__': main()
