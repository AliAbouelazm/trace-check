import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import data from '../web/review-model-data.js';
import {REVIEW_MODEL} from '../web/review-model-info.js';
import {parseArtifact,score} from '../web/experimental.js';
test('frozen reconstructed artifact matches recorded bytes, hash, cutoff and Python goldens',()=>{
  assert.equal(Buffer.byteLength(data),REVIEW_MODEL.bytes);
  assert.equal(createHash('sha256').update(data).digest('hex'),REVIEW_MODEL.sha256);
  const model=parseArtifact(data);
  assert.equal(model.threshold,.7);
  assert.equal(REVIEW_MODEL.automatic_promotion_eligible,false);
  const golden=JSON.parse(readFileSync(new URL('./fixtures/reconstructed-model-golden.json',import.meta.url)));
  for(const item of golden){
    const actual=score(model,item.text);
    assert.equal(actual.suggestion,item.expected.suggestion);
    assert.equal(actual.abstention,item.expected.abstention);
    if(item.expected.scores===null)assert.equal(actual.scores,null);
    else actual.scores.forEach((value,i)=>assert.ok(Math.abs(value-item.expected.scores[i])<=1e-6));
  }
});
