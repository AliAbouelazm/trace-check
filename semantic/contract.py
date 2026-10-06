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

def message_with_audit(message):
    if message['role'] not in ('user','assistant','tool'):return '',{'excluded_role':True,'fields':[],'tool_spans':[]}
    content=clean(message.get('content') or '')
    text=message['role']+' '+content[:4000]
    fields=[{'field':'content','characters_before':len(content),'characters_retained':min(len(content),4000)}]
    spans=[]
    for index,call in enumerate(message.get('tool_calls') or []):
        function=call['function'];argument=clean(function.get('arguments',''))
        part=str(function['name'])+' '+argument[:4000]
        start=len(text)+1;text+='\n'+part
        spans.append({'index':index,'start':start,'end':len(text)})
        fields.append({'field':'tool_arguments','index':index,'characters_before':len(argument),'characters_retained':min(len(argument),4000)})
    return text,{'excluded_role':False,'fields':fields,'tool_spans':spans}

def message_text(message):
    return message_with_audit(message)[0]

def parts_with_audit(row,index):
    messages=row['messages']
    last=max(i for i,message in enumerate(messages) if message['role']=='assistant')
    if type(index) is not int or not 0<=index<last or messages[index]['role']!='assistant':raise ValueError('Only nonfinal assistant actions')
    task=clean(row['question'])
    previous=[message_with_audit(m) for m in messages[max(0,index-2):index]]
    prefix='\n'.join(text for text,_ in previous if text)
    action,current=message_with_audit(messages[index])
    spans=[{**span,'characters_retained':max(0,min(span['end'],12000)-span['start']),
            'removed_entirely':span['start']>=12000} for span in current['tool_spans']]
    result={'task':task[:4000],'prefix':prefix[-12000:],'action':action[:12000]}
    audit={'characters':{key:{'before':len(value),'retained':len(result[key]),'removed':len(value)-len(result[key])} for key,value in [('task',task),('prefix',prefix),('action',action)]},
           'message_fields':{'previous':[a for _,a in previous],'action':current},
           'action_tool_spans':spans,
           'counts_after_answer_tag_removal':True}
    return result,audit

def parts(row,index):
    return parts_with_audit(row,index)[0]

def allocate(task_ids,prefix_ids,action_ids,cls_id,sep_id):
    """Two independent <=256-WordPiece streams; allocation fixed before data."""
    ids={'task':task_ids,'prefix':prefix_ids,'action':action_ids}
    caps={'task':64,'prefix':190,'action':254}
    return {'context':[cls_id]+list(task_ids[:64])+list(prefix_ids[-190:])+[sep_id],
            'action':[cls_id]+list(action_ids[:254])+[sep_id],
            'truncated':{key:len(value)>caps[key] for key,value in ids.items()},
            'token_counts':{key:{'before':len(value),'retained':min(len(value),caps[key]),'removed':max(0,len(value)-caps[key])} for key,value in ids.items()}}

def mean_normalize(tokens,mask):
    active=[row for row,keep in zip(tokens,mask) if keep]
    if len(tokens)!=len(mask) or not active:raise ValueError('Invalid attention mask')
    width=len(active[0])
    if not width or any(len(row)!=width for row in tokens):raise ValueError('Invalid token dimensions')
    vector=[sum(row[i] for row in active)/len(active) for i in range(width)]
    norm=math.sqrt(sum(x*x for x in vector))
    if not math.isfinite(norm) or norm==0:raise ValueError('Nonfinite or empty embedding')
    return [x/norm for x in vector]

def tool_call_token_audit(tokenizer, text, spans, limit):
    offsets=tokenizer.encode(text,add_special_tokens=False).offsets
    retained=offsets[:limit]
    return [{'index':span['index'],'tokens_before_limit':sum(a<span['end'] and b>span['start'] for a,b in offsets),
             'tokens_retained':sum(a<span['end'] and b>span['start'] for a,b in retained),
             'removed_entirely':not any(a<span['end'] and b>span['start'] for a,b in retained)} for span in spans]
