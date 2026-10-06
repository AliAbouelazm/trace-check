"""Synthetic parity support and JSON export only. No fitting or data loading."""
import collections
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'research'))
from adapter import adapt, feature

MAX_BYTES = 2 * 1024 * 1024

def make_envelope(row):
    """Keep original message slots and explicit step mappings, without references."""
    run = adapt(row)
    groups = []
    position = 0
    for message in row['messages']:
        role = message['role']
        count = 0 if role == 'system' else 1 + (len(message.get('tool_calls') or []) if role == 'assistant' else 0)
        groups.append({'role': 'excluded' if role == 'system' else role,
                       'step_ids': [step['id'] for step in run['steps'][position:position + count]]})
        position += count
    result = {'envelope_version':1, 'run':run, 'messages':groups}
    if len(groups) > 2000 or len(run['steps']) > 2000:
        raise ValueError('Envelope exceeds grouping/step limit')
    encode(result)
    return result

def encode(value):
    result = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(result.encode('utf-8')) > MAX_BYTES:
        raise ValueError('JSON exceeds 2 MiB contract')
    return result

def reference_feature(envelope, index):
    """Reconstruct original slots, then use the untouched frozen feature oracle."""
    by_id = {step['id']:step for step in envelope['run']['steps']}
    messages = []
    for group in envelope['messages']:
        if group['role'] == 'excluded':
            messages.append({'role':'system','content':''})
            continue
        main, *calls = [by_id[key] for key in group['step_ids']]
        message = {'role':group['role'], 'content':main['content']}
        if calls:
            message['tool_calls'] = [{'function':{'name':step['tool'],'arguments':step['content']}} for step in calls]
        messages.append(message)
    if not 0 <= index < len(messages) or messages[index]['role'] != 'assistant':
        raise ValueError('Only assistant messages may be scored')
    return feature({'messages':messages}, index)

def artifact(vocabulary, idf, coefficients, intercept, threshold=.5, provenance=None):
    """Serialize primitives, never pickle/joblib. No quantization or truncation."""
    n = len(vocabulary)
    if not 1 <= n <= 20000 or len(set(vocabulary)) != n or any(not isinstance(t,str) or not t or len(t.encode('utf-16-le'))//2 > 200 for t in vocabulary):
        raise ValueError('Invalid vocabulary')
    def vector(values, size, low, high):
        return len(values) == size and all(type(v) in (int,float) and math.isfinite(v) and low <= v <= high for v in values)
    if not vector(idf,n,1,100) or not vector(intercept,3,-1000,1000) or len(coefficients) != 3 or not all(vector(row,n,-1000,1000) for row in coefficients):
        raise ValueError('Invalid model dimensions or values')
    if threshold not in (.5,.6,.7,.8,.9,.95): raise ValueError('Unsupported threshold')
    p = provenance or {'kind':'synthetic','source_hashes':[],'split_sha256':None}
    if set(p) != {'kind','source_hashes','split_sha256'} or p['kind'] not in ('synthetic','train-validation') or not isinstance(p['source_hashes'],list) or len(p['source_hashes']) > 4:
        raise ValueError('Invalid provenance')
    valid_hash = lambda s: isinstance(s,str) and re.fullmatch('[0-9a-f]{64}',s)
    if not all(valid_hash(h) for h in p['source_hashes']): raise ValueError('Invalid source hashes')
    if p['kind'] == 'synthetic':
        if p['source_hashes'] or p['split_sha256'] is not None: raise ValueError('Invalid synthetic provenance')
    elif not p['source_hashes'] or not valid_hash(p['split_sha256']): raise ValueError('Missing training provenance')
    result = {'artifact_version':1,'feature_contract':'original-messages-v1','tokenizer':'sklearn-ascii-v1','classes':[-1,0,1],
              'vocabulary':vocabulary,'idf':idf,'coefficients':coefficients,'intercept':intercept,'threshold':threshold,'provenance':p}
    encode(result)
    return result

def reference_score(model, text):
    if len(text) > 12000: raise ValueError('Feature exceeds contract')
    def abstain(reason): return {'abstention':reason,'scores':None,'suggestion':False}
    if not text.isascii(): return abstain('unsupported-unicode')
    tokens = re.findall(r'(?u)\b\w\w+\b', text.lower())
    counts = collections.Counter(tokens)
    counts.update(' '.join(pair) for pair in zip(tokens,tokens[1:]))
    weighted = [(i,(1+math.log(counts[term]))*model['idf'][i]) for i,term in enumerate(model['vocabulary']) if counts[term]]
    if not weighted: return abstain('no-known-features')
    norm = math.sqrt(sum(v*v for _,v in weighted))
    logits = [bias + sum(row[i]*v/norm for i,v in weighted) for bias,row in zip(model['intercept'],model['coefficients'])]
    exps = [math.exp(v-max(logits)) for v in logits]
    scores = [v/sum(exps) for v in exps]
    boundary = abs(scores[0]-model['threshold']) <= 1e-6
    return {'scores':scores,'suggestion':not boundary and scores[0] > model['threshold'],
            'abstention':'threshold-ambiguity' if boundary else 'below-threshold' if scores[0] < model['threshold'] else None}
