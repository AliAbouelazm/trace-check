"""Predeclared validation-only threshold gate. No model fitting or test access."""
import math
THRESHOLDS=(.50,.60,.70,.80,.90,.95)

def choose_threshold(rows, validation_groups):
    if not rows or not validation_groups: raise ValueError('Validation rows and frozen groups required')
    for row in rows:
        if row['split'] != 'validation' or row['group'] not in validation_groups or row['label'] not in (-1,0,1) or type(row['rule']) is not bool:
            raise ValueError('Only frozen validation records are allowed')
        score=row['score']
        if score is not None and (type(score) not in (int,float) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError('Invalid validation score')
    def metrics(predictions):
        tp=sum(p and r['label']==-1 for r,p in zip(rows,predictions))
        fp=sum(p and r['label']!=-1 for r,p in zip(rows,predictions))
        fn=sum(not p and r['label']==-1 for r,p in zip(rows,predictions))
        tn=len(rows)-tp-fp-fn
        return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'flags':tp+fp,'recall':tp/(tp+fn) if tp+fn else 0,
                'precision':tp/(tp+fp) if tp+fp else 0,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,
                'neutral_fp':sum(p and r['label']==0 for r,p in zip(rows,predictions)),
                'positive_fp':sum(p and r['label']==1 for r,p in zip(rows,predictions)),
                'subset_fp':{s:sum(p and r['label']!=-1 and r['subset']==s for r,p in zip(rows,predictions)) for s in sorted({r['subset'] for r in rows})}}
    rules=[r['rule'] for r in rows]; baseline=metrics(rules)
    def within_budget(m):
        return m['fp'] <= baseline['fp'] and m['neutral_fp'] <= baseline['neutral_fp'] and all(n <= baseline['subset_fp'][s] for s,n in m['subset_fp'].items())
    candidates=[]
    for threshold in THRESHOLDS:
        predictions=[r['score'] is not None and r['score'] > threshold and abs(r['score']-threshold)>1e-6 for r in rows]
        model=metrics(predictions);combined=metrics([a or b for a,b in zip(rules,predictions)])
        candidates.append({'threshold':threshold,'model':model,'combined':combined,
                           'eligible':model['flags']>=20 and within_budget(model) and within_budget(combined)})
    eligible=[c for c in candidates if c['eligible']]
    selected=max(eligible,key=lambda c:(c['model']['recall'],c['threshold'])) if eligible else None
    return {'rules':baseline,'candidates':candidates,'selected_threshold':selected['threshold'] if selected else None,
            'interpretation':'Development validation only; examined test split is not a fresh assessment.'}
