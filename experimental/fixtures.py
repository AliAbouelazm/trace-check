"""Handwritten synthetic data and coefficients, never trained weights."""
import copy
import math
from contract import make_envelope, artifact, reference_feature, reference_score

def fixtures():
    base = {'query_index':0,'sample_index':0,'question':'Find project files','messages':[
        {'role':'user','content':'Find files'},
        {'role':'assistant','content':'Checking now','tool_calls':[
            {'id':'c1','function':{'name':'search','arguments':{'query':'file', 'count':2}}},
            {'id':'c2','function':{'name':'lookup','arguments':'{"path":"."}'}}]},
        {'role':'system','content':'SYSTEM_PRIVATE'},
        {'role':'tool','name':'lookup','tool_call_id':'c2','content':'failed <ANSWER>HIDDEN ANSWER</ANSWER> missing file'},
        {'role':'assistant','content':'Checking again'},
        {'role':'assistant','content':'FINAL_PRIVATE'}]}
    rows = [base]
    for content in ['No calls here', '🙂'*4100+'tail', 'café Σ 𐐀 ²', '<anſwer>HIDDEN</anſwer> visible', 'prefix <answer>SECRET\nMULTILINE</answer> suffix', 'x'*4001]:
        row=copy.deepcopy(base); row['messages'][1]['content']=content; rows.append(row)
    row=copy.deepcopy(base)
    row['messages'][1]['tool_calls']=[{'id':str(i),'function':{'name':'search','arguments':'🙂'*4100}} for i in range(4)]
    rows.append(row)
    row=copy.deepcopy(base); row['messages'][1]['tool_calls']=[]; rows.append(row)
    row=copy.deepcopy(base); row['messages'][1]['tool_calls']=row['messages'][1]['tool_calls'][:1]; rows.append(row)
    envelopes=[make_envelope(row) for row in rows]
    vocabulary=['assistant','checking','failed','file','checking now','failed missing','search','lookup','again','aa','aa aa','__','123']
    model=artifact(vocabulary,[1+i/10 for i in range(len(vocabulary))],[[math.sin(i+k) for i in range(len(vocabulary))] for k in range(3)],[.1,-.2,.3])
    feature_cases=[]
    for ei,envelope in enumerate(envelopes):
        for index in [1,4]: feature_cases.append({'envelope':ei,'index':index,'expected':reference_feature(envelope,index)})
    texts=[c['expected'] for c in feature_cases]+['AA aa aa __ 123 x !', 'unknown-only', 'a.a.a', 'İ Σ café', 'failed file checking', '']
    score_cases=[{'text':t,'expected':reference_score(model,t)} for t in texts]
    boundary=artifact(['aa'],[1],[[0],[0],[0]],[math.log(2),0,0])
    return {'envelopes':envelopes,'model':model,'feature_cases':feature_cases,'score_cases':score_cases,
            'boundary_model':boundary,'boundary_expected':reference_score(boundary,'aa')}

if __name__ == '__main__':
    import json
    print(json.dumps(fixtures(),ensure_ascii=False))
