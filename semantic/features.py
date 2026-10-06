"""Frozen v2 prefix/action allocation. Pure tokenization, no data access or labels."""
from .contract import clean, message_with_audit

FEATURE_VERSION='semantic-v2-text94-tools4x40-args16head15tail-context64x190'
MAX_CALLS=4

def prepare_input(row,index):
    messages=row['messages']
    last=max(i for i,m in enumerate(messages) if m['role']=='assistant')
    if type(index) is not int or not 0<=index<last or messages[index]['role']!='assistant':
        raise ValueError('Only nonfinal assistant actions')
    task=clean(row['question'])
    previous=[message_with_audit(m) for m in messages[max(0,index-2):index]]
    prefix='\n'.join(text for text,_ in previous if text)
    current=messages[index];content=clean(current.get('content') or '')
    calls=[];call_audits=[]
    for call in current.get('tool_calls') or []:
        function=call['function'];name=clean(function['name']);argument=clean(function.get('arguments',''))
        calls.append({'name':name[:128],'arguments':argument if len(argument)<=4000 else argument[:2000]+argument[-2000:]})
        call_audits.append({'name_characters':counts(len(name),128),'argument_characters':counts(len(argument),4000)})
    return {'task':task[:4000],'prefix':prefix[-12000:],'text':'assistant '+content[:4000],'calls':calls[:MAX_CALLS],
            'call_count':len(calls),'name_character_overflow':any(a['name_characters']['removed'] for a in call_audits)}, {'characters':{'task':counts(len(task),4000),'prefix':counts(len(prefix),12000),'text':counts(len(content),4000)},
            'previous_fields':[a for _,a in previous],'calls':call_audits,'counts_after_answer_tag_removal':True}

def counts(length,cap):
    return {'before':length,'retained':min(length,cap),'removed':max(0,length-cap)}

def tokenize(prepared,tokenizer):
    """IDs only from allowlisted input; labels and split IDs never enter encoder."""
    cls=tokenizer.token_to_id('[CLS]');sep=tokenizer.token_to_id('[SEP]');unk=tokenizer.token_to_id('[UNK]')
    if any(x is None for x in (cls,sep,unk)):raise ValueError('Required official special tokens missing')
    fields={key:tokenizer.encode(prepared[key],add_special_tokens=False).ids for key in ('task','prefix','text')}
    calls=[{key:tokenizer.encode(call[key],add_special_tokens=False).ids for key in ('name','arguments')} for call in prepared['calls']]
    audits={key:{**counts(len(ids),{'task':64,'prefix':190,'text':94 if prepared['call_count'] else 254}[key]),'unknown_before':ids.count(unk)} for key,ids in fields.items()}
    text=fields['text'][:94 if prepared['call_count'] else 254]
    action=[cls]+text;call_audits=[];reason='tool-name-exceeds-128-characters' if prepared['name_character_overflow'] else None
    if prepared['call_count']>MAX_CALLS:reason='more-than-four-current-calls'
    for call,original in zip(calls,prepared['calls']):
        name=call['name'][:8];args=call['arguments'] if len(call['arguments'])<=31 else call['arguments'][:16]+call['arguments'][-15:]
        if len(call['name'])>8:reason=reason or 'tool-name-exceeds-eight-tokens'
        if not name or all(token==unk for token in name):reason=reason or 'unknown-or-empty-tool-name'
        if original['arguments'].strip() and (not args or all(token==unk for token in args)):
            reason=reason or 'unknown-only-tool-arguments'
        action.extend(name+args+[sep])
        call_audits.append({key:{**counts(len(call[key]),cap),'unknown_before':call[key].count(unk),'unknown_retained':kept.count(unk)} for key,cap,kept in [('name',8,name),('arguments',31,args)]})
    # Exclude the literal role marker when checking meaningful no-tool content.
    if not calls:
        content=tokenizer.encode(prepared['text'][len('assistant '):],add_special_tokens=False).ids[:253]
        if not content or all(token==unk for token in content):reason=reason or 'empty-or-unknown-only-action'
    action.append(sep)
    context=[cls]+fields['task'][:64]+fields['prefix'][-190:]+[sep]
    if max(len(context),len(action))>256:raise ValueError('Token budget exceeded')
    for key,ids in [('task',fields['task'][:64]),('prefix',fields['prefix'][-190:]),('text',text)]:audits[key]['unknown_retained']=ids.count(unk)
    return {'context':context,'action':action}, {'fields':audits,'calls':call_audits,'unrepresented_calls':max(0,prepared['call_count']-MAX_CALLS),'support_reason':reason}
