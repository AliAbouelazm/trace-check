"""Proposed semantic input contract; standard-library tests, no encoder or fit."""
import json
import math
import re

MODEL_ID='sentence-transformers/all-MiniLM-L6-v2'
REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
WEIGHTS={
    'model.safetensors':(90868376,'53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db'),
    'onnx/model.onnx':(90405214,'6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452')}

def clean(value):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
    return re.sub(r'<answer>.*?</answer>','[answer omitted]',text,flags=re.S|re.I)

def message_text(message):
    if message['role'] not in ('user','assistant','tool'):return ''
    parts=[message['role']+' '+clean(message.get('content') or '')[:4000]]
    for call in message.get('tool_calls') or []:
        function=call['function']
        parts.append(str(function['name'])+' '+clean(function.get('arguments',''))[:4000])
    return '\n'.join(parts)

def parts(row,index):
    messages=row['messages']
    last=max(i for i,message in enumerate(messages) if message['role']=='assistant')
    if type(index) is not int or not 0<=index<last or messages[index]['role']!='assistant':raise ValueError('Only nonfinal assistant actions')
    return {'task':clean(row['question'])[:4000],
            'prefix':'\n'.join(filter(None,(message_text(m) for m in messages[max(0,index-2):index])))[-12000:],
            'action':message_text(messages[index])[:12000]}

def allocate(task_ids,prefix_ids,action_ids,cls_id,sep_id):
    """Two independent <=256-WordPiece streams; allocation fixed before data."""
    return {'context':[cls_id]+list(task_ids[:64])+list(prefix_ids[-190:])+[sep_id],
            'action':[cls_id]+list(action_ids[:254])+[sep_id],
            'truncated':{'task':len(task_ids)>64,'prefix':len(prefix_ids)>190,'action':len(action_ids)>254}}

def mean_normalize(tokens,mask):
    active=[row for row,keep in zip(tokens,mask) if keep]
    if len(tokens)!=len(mask) or not active:raise ValueError('Invalid attention mask')
    width=len(active[0])
    if not width or any(len(row)!=width for row in tokens):raise ValueError('Invalid token dimensions')
    vector=[sum(row[i] for row in active)/len(active) for i in range(width)]
    norm=math.sqrt(sum(x*x for x in vector))
    if not math.isfinite(norm) or norm==0:raise ValueError('Nonfinite or empty embedding')
    return [x/norm for x in vector]
