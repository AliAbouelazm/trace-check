"""Offline CPU-only encoder and JSON head arithmetic. No fitting or data access."""
import hashlib
import json
from pathlib import Path
from .contract import REVISION,WEIGHTS
from .provenance import verify_lock

class Encoder:
    def __init__(self,directory):
        self.sizes=verify_lock(directory,REVISION)
        path=directory/'onnx/model.onnx';size,sha=WEIGHTS['onnx/model.onnx']
        if any(p.is_symlink() for p in (path,*path.parents)) or path.stat().st_size!=size:
            raise ValueError('Invalid ONNX source')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=sha:raise ValueError('ONNX hash mismatch')
        self.sizes['onnx/model.onnx']=size
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.np=np;self.tokenizer=Tokenizer.from_file(str(directory/'tokenizer.json'))
        self.tokenizer.no_truncation();self.tokenizer.no_padding()
        self.pad=self.tokenizer.token_to_id('[PAD]')
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
        if self.session.get_providers()!=['CPUExecutionProvider']:raise ValueError('CPU only')
    def encode(self,streams):
        np=self.np
        if not 1<=len(streams)<=8 or any(not 2<=len(s)<=256 for s in streams):raise ValueError('Fixed batch/sequence cap')
        values=np.full((len(streams),max(map(len,streams))),self.pad,dtype=np.int64);mask=np.zeros_like(values)
        for i,ids in enumerate(streams):values[i,:len(ids)]=ids;mask[i,:len(ids)]=1
        feed={'input_ids':values,'attention_mask':mask,'token_type_ids':np.zeros_like(values)}
        output=self.session.run(None,{i.name:feed[i.name] for i in self.session.get_inputs()})[0]
        if output.shape!=(len(streams),values.shape[1],384):raise ValueError('Encoder dimensions')
        active=mask[...,None].astype(np.float32)
        pooled=(output*active).sum(1)/active.sum(1).clip(min=1e-9)
        norms=np.linalg.norm(pooled,axis=1,keepdims=True)
        if not np.isfinite(pooled).all() or (norms==0).any():raise ValueError('Invalid embeddings')
        vectors=pooled/norms
        if not np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5):raise ValueError('Invalid normalization')
        return vectors

def head_probabilities(vectors,head):
    import numpy as np
    coefficients=np.asarray(head['coefficients'],dtype=np.float64);intercept=np.asarray(head['intercept'],dtype=np.float64)
    if head['classes']!=[-1,0,1] or coefficients.shape!=(3,768) or intercept.shape!=(3,) or not np.isfinite(coefficients).all() or not np.isfinite(intercept).all():
        raise ValueError('Invalid JSON head')
    logits=np.asarray(vectors,dtype=np.float64)@coefficients.T+intercept
    values=np.exp(logits-logits.max(axis=1,keepdims=True));return values/values.sum(axis=1,keepdims=True)
