"""No-fit audit against sklearn 1.8.0 using manually assigned synthetic weights."""
import json
from unittest.mock import patch
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from fixtures import fixtures
from contract import reference_score
assert sklearn.__version__ == '1.8.0', 'Use pinned research dependencies for pre-fit audit'
data=fixtures();model=data['model']
with patch.object(TfidfVectorizer,'fit',side_effect=AssertionError('No fit allowed')), patch.object(TfidfVectorizer,'fit_transform',side_effect=AssertionError('No fit allowed')), patch.object(LogisticRegression,'fit',side_effect=AssertionError('No fit allowed')):
    vectorizer=TfidfVectorizer(vocabulary={t:i for i,t in enumerate(model['vocabulary'])},ngram_range=(1,2),sublinear_tf=True)
    vectorizer.idf_=np.array(model['idf'])
    classifier=LogisticRegression()
    classifier.classes_=np.array(model['classes'])
    classifier.coef_=np.array(model['coefficients'])
    classifier.intercept_=np.array(model['intercept'])
    classifier.n_features_in_=len(model['vocabulary'])
    errors=[]
    for case in data['score_cases']:
        expected=reference_score(model,case['text'])
        if expected['scores'] is None:continue
        actual=classifier.predict_proba(vectorizer.transform([case['text']]))[0]
        errors.append(float(np.max(np.abs(actual-expected['scores']))))
    assert errors and max(errors)<=1e-6
print(json.dumps({'sklearn':sklearn.__version__,'no_fit':True,'numeric_cases':len(errors),'max_score_absolute_error':max(errors)}))
