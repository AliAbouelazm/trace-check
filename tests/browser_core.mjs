import test from 'node:test';
import assert from 'node:assert/strict';
import {validateRun, analyzeRun, redactRun, makeReport} from '../web/core.js';
import {examples} from '../web/examples.js';
const base = () => structuredClone(examples[0].run);
test('canonical validation rejects malformed and unsupported fields', () => {
  for (const value of [null, [], {}, {...base(), label: true}, {...base(), status: 'running'}, {...base(), steps: []}, {...base(), steps: [{id:'x',kind:'assistant',content:'',groundtruth:'secret'}]}]) assert.throws(() => validateRun(value));
  const duplicate = base(); duplicate.steps.push(duplicate.steps[0]); assert.throws(() => validateRun(duplicate));
  assert.deepEqual(validateRun(base()), base());
});
test('rules preserve uncertainty around neutral exploration', () => {
  const flags = analyzeRun(base()); assert.equal(flags.length, 1); assert.equal(flags[0].rule, 'tool_error'); assert.match(flags[0].uncertainty, /exploration/);
});
test('structural rules distinguish order and repeated calls', () => {
  const flags = analyzeRun(examples[1].run); assert.deepEqual(flags.map(f=>f.rule).sort(), ['missing_result','repeated_call','unmatched_result']);
  const run = base(); run.steps = [{id:'1',kind:'tool_result',call_id:'a',content:'ok'},{id:'2',kind:'tool_call',call_id:'a',content:'x'}];
  assert.deepEqual(analyzeRun(run).map(f=>f.rule), ['unmatched_result','missing_result']);
});
test('redaction removes likely secrets and emails, leaving source unchanged', () => {
  const run = base(); run.task = 'Contact demo@example.com password=supersecret sk-abcdefghijklmnop';
  const safe = redactRun(run); assert.equal(safe.redactionCount,3); assert.doesNotMatch(safe.run.task,/demo@example|supersecret|abcdefghijkl/); assert.match(run.task,/supersecret/);
  assert.match(makeReport(safe.run,[],3).review_method,/No trained model/);
});
test('JSON quoted secrets and bearer credentials are redacted', () => {
  const run = base(); run.task = '{"password":"hunter2","api_key":"abcdefgh","Authorization":"Bearer abcxyz"}';
  const safe = redactRun(run); assert.equal(safe.redactionCount,3); assert.doesNotMatch(safe.run.task,/hunter2|abcdefgh|abcxyz/);
});
test('sensitive identifiers are mapped to unique stable links', () => {
  const run = base(); run.steps = [
    {id:'one@example.com',kind:'tool_call',call_id:'secret@example.com',content:'one'},
    {id:'two@example.com',kind:'tool_result',call_id:'secret@example.com',content:'ok'}
  ];
  const safe = redactRun(run).run; assert.notEqual(safe.steps[0].id,safe.steps[1].id); assert.equal(safe.steps[0].call_id,safe.steps[1].call_id); assert.deepEqual(analyzeRun(safe),[]);
});
test('text error evidence includes the matched observation', () => {
  const run = base(); run.steps = [{id:'1',kind:'tool_result',content:'Request failed with code 500'}];
  assert.match(analyzeRun(run)[0].evidence,/failed with code 500/);
});
test('evidence redacts full secrets before excerpt boundaries can cut off their prefix', () => {
  const run = base();
  const secret = 'sk-' + 'a'.repeat(70) + '-failed-' + 'b'.repeat(70);
  run.steps = [{id:'1',kind:'tool_result',content:secret}];
  const flags = analyzeRun(run);
  assert.equal(flags.length, 1);
  assert.doesNotMatch(flags[0].evidence, /a{10}|b{10}/);
});
test('schema rejects prototype keys and exact field and step limit violations', () => {
  assert.throws(() => validateRun(JSON.parse('{"__proto__":{}}')));
  for (const edit of [r => r.schema_version = 2, r => r.steps = Array.from({length:2001}, (_,i) => ({id:String(i),kind:'assistant',content:''})), r => r.task = 'x'.repeat(20001), r => r.steps[0].content = 'x'.repeat(100001)]) {
    const run = base(); edit(run); assert.throws(() => validateRun(run));
  }
});
