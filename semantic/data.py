"""Frozen source routing. TEST bodies never reach preparation, rules or encoding."""
import collections
import hashlib
import json
from pathlib import Path

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
    if Path(data).is_symlink() or any(p.is_symlink() for p in Path(data).glob('*.jsonl')):raise ValueError('Symlink data forbidden')
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
                  'validation_groups':sorted({root(k) for k,v in groups.items() if v=='validation'}),
                  'groups_by_split':{s:sorted({root(k) for k,v in groups.items() if v==s}) for s in ('train','validation','test')},
                  'groups_by_split_subset':{s:{subset:sorted({root(k) for k,v in groups.items() if v==s and k.rsplit(':',1)[0]==subset}) for subset in sorted({k.rsplit(':',1)[0] for k in groups})} for s in ('train','validation','test')}}
