import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {parseEnvelope,parseArtifact,feature,score,MODEL_BYTES} from '../web/experimental.js';
const fixture=JSON.parse(execFileSync('python3',['experimental/fixtures.py'],{maxBuffer:4*1024*1024}));
const envelopes=fixture.envelopes.map(value=>parseEnvelope(JSON.stringify(value)));
const model=parseArtifact(JSON.stringify(fixture.model));
function equalScore(actual, expected) {
  assert.equal(actual.abstention,expected.abstention); assert.equal(actual.suggestion,expected.suggestion);
  if (expected.scores === null) assert.equal(actual.scores,null);
  else actual.scores.forEach((v,i)=>assert.ok(Math.abs(v-expected.scores[i]) <= 1e-6));
}
test('Python/JS features preserve original groups, nonstring arguments, Unicode and bounds',()=>{
  for(const c of fixture.feature_cases) assert.equal(feature(envelopes[c.envelope],c.index),c.expected);
  for(const env of envelopes) {
    assert.throws(()=>feature(env,env.groups.length-1));
    assert.throws(()=>feature(env,2));
    assert.throws(()=>feature(env,-1));
  }
  assert.ok(fixture.feature_cases.some(c=>Array.from(c.expected).length === 12000));
  assert.ok(fixture.feature_cases.every(c=>!c.expected.includes('FINAL_PRIVATE') && !c.expected.includes('SYSTEM_PRIVATE')));
  const env=structuredClone(envelopes[0]); env.groups[3].steps[0].content='FUTURE_POISON';
  assert.equal(feature(env,1),feature(envelopes[0],1));
});
test('Python/JS TF-IDF and stable softmax parity, abstention and threshold ambiguity',()=>{
  for(const c of fixture.score_cases) equalScore(score(model,c.text),c.expected);
  equalScore(score(parseArtifact(JSON.stringify(fixture.boundary_model)),'aa'),fixture.boundary_expected);
  assert.equal(fixture.boundary_expected.abstention,'threshold-ambiguity');
  assert.throws(()=>score(model,'x'.repeat(12001)));
});
test('grouping rejects arbitrary v1, extra data, duplicates, reorder and missing mappings',()=>{
  assert.throws(()=>parseEnvelope(JSON.stringify(fixture.envelopes[0].run)));
  for(const change of [
    e=>e.envelope_version=2,e=>e.labels=[],e=>e.messages[2].content='system',
    e=>e.messages[1].step_ids.reverse(),e=>e.messages[1].step_ids.push(e.messages[1].step_ids[0]),
    e=>e.messages.pop(),e=>e.messages[1].role='tool',e=>e.messages=Array(2001).fill({role:'excluded',step_ids:[]})
  ]){const e=structuredClone(fixture.envelopes[0]);change(e);assert.throws(()=>parseEnvelope(JSON.stringify(e)));}
  assert.throws(()=>parseEnvelope(' '.repeat(MODEL_BYTES+1)));
});
test('JSON model rejects executable/unknown fields, shapes, nonfinite numbers and size violations',()=>{
  for(const change of [
    a=>a.artifact_version=2,a=>a.code='alert(1)',a=>a.classes.reverse(),a=>a.threshold=.55,
    a=>a.vocabulary[1]=a.vocabulary[0],a=>a.idf[0]=null,a=>a.idf[0]=0,a=>a.idf.pop(),
    a=>a.coefficients[0][0]=1e4,a=>a.intercept=[0],a=>a.provenance.kind='test',
    a=>a.provenance={kind:'train-validation',source_hashes:[],split_sha256:null},
    a=>a.vocabulary=Array(20001).fill('bad'),a=>a.vocabulary[0]='x'.repeat(201)
  ]){const a=structuredClone(fixture.model);change(a);assert.throws(()=>parseArtifact(JSON.stringify(a)));}
  const valid=JSON.stringify(fixture.model);
  assert.throws(()=>parseArtifact(valid.replace('"idf":[1,','"idf":[1e999,')));
  assert.throws(()=>parseArtifact(' '.repeat(MODEL_BYTES+1)));
  assert.throws(()=>parseArtifact('🙂'.repeat(MODEL_BYTES/2)));
  assert.throws(()=>parseArtifact('{"__proto__":{}}'));
});
