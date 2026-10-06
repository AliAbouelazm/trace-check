"""Fail-closed offline source and runtime verification. Never downloads."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

REQUIRED_FILES=frozenset('config.json tokenizer.json tokenizer_config.json special_tokens_map.json vocab.txt sentence_bert_config.json 1_Pooling/config.json modules.json config_sentence_transformers.json'.split())
REQUIRED_PACKAGES=frozenset('numpy torch transformers tokenizers onnxruntime safetensors huggingface-hub'.split())

def verify_lock(directory, revision, lock_path=None, version=importlib.metadata.version):
    lock=json.loads((lock_path or Path(__file__).with_name('runtime-lock.json')).read_text())
    if lock.get('verified') is not True or lock.get('revision')!=revision:
        raise ValueError('Verified source/runtime pins required before preflight')
    if set(lock.get('files',{}))!=REQUIRED_FILES or set(lock.get('packages',{}))!=REQUIRED_PACKAGES:
        raise ValueError('Incomplete runtime lock')
    sizes={}
    for name,entry in lock['files'].items():
        size=entry.get('bytes');digest=entry.get('sha256')
        source='https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/'+revision+'/'+name
        if type(size) is not int or not 0<size<=2*1024*1024 or not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest) or entry.get('source')!=source:
            raise ValueError('Invalid source pin')
        path=directory/name
        if directory.is_symlink() or any(p.is_symlink() for p in [path,*path.parents] if p!=directory.parent):
            raise ValueError('Symlink model paths forbidden')
        if not path.is_file() or path.stat().st_size!=size or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Tokenizer/config digest mismatch: '+name)
        sizes[name]=size
    for name,expected in lock['packages'].items():
        if not isinstance(expected,str) or not re.fullmatch(r'[0-9][A-Za-z0-9.+!-]*',expected) or version(name)!=expected:
            raise ValueError('Exact dependency pin mismatch: '+name)
    return sizes
