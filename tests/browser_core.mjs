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
test('quoted named secrets consume spaces, delimiters, escapes and newlines', () => {
  const cases = [
    ['{"password":"correct horse battery staple"}', '{"password":"[REDACTED]"}'],
    ['api_key="abc;def,ghi" next=ordinary', 'api_key="[REDACTED]" next=ordinary'],
    [String.raw`password="first \"hidden quote\" trailing" next=ordinary`, 'password="[REDACTED]" next=ordinary'],
    [String.raw`secret='first \'hidden quote\' trailing' next=ordinary`, "secret='[REDACTED]' next=ordinary"],
    [String.raw`access_token="first \\ last"`, 'access_token="[REDACTED]"'],
    ['password="first\nsecond" next=ordinary', 'password="[REDACTED]" next=ordinary'],
    ['secret="unterminated value\ntrailing', 'secret="[REDACTED]'],
    ['Authorization: Bearer opaque-token', 'Authorization: [REDACTED]'],
    ['password=opaque-token next=ordinary', 'password=[REDACTED] next=ordinary'],
    ['The password field is required; key=value; ordinary="two words"', 'The password field is required; key=value; ordinary="two words"']
  ];
  for (const [input, expected] of cases) assert.equal(redactRun(input).run, expected);
});
test('quoted secret suffixes cannot leak into evidence excerpts or redacted reports', () => {
  const run = base();
  run.task = '{"password":"correct horse battery staple"}';
  run.steps = [{id:'1',kind:'tool_result',content:String.raw`failed api_key="abc;def,ghi \"hidden\" trailing"`}];
  const safe = redactRun(run);
  const flags = redactRun(analyzeRun(run)).run;
  const report = JSON.stringify(makeReport(safe.run, flags, safe.redactionCount));
  assert.doesNotMatch(report, /correct|horse|battery|staple|abc|def,ghi|hidden|trailing/);
  assert.match(flags[0].evidence, /failed api_key=/);
  assert.match(report, /Redaction is best effort/);
});
test('email candidates redact ordinary addresses and preserve non-address text', () => {
  assert.equal(redactRun('one@example.com; two+tag@sub.example.org').run, '[REDACTED EMAIL]; [REDACTED EMAIL]');
  assert.equal(redactRun('Contact one@example.com.').run, 'Contact [REDACTED EMAIL].');
  assert.equal(redactRun('version.a.b @ local@host ordinary').run, 'version.a.b @ local@host ordinary');
});
test('maximum-size adversarial email candidates stay within CPU budget', () => {
  for (const suffix of ['', '@']) {
    const content = 'a.'.repeat(50000).slice(0, 100000 - suffix.length) + suffix;
    const run = base();
    run.steps = Array.from({length:20}, (_, i) => ({id:String(i),kind:'assistant',content}));
    assert.ok(Buffer.byteLength(JSON.stringify(run)) <= 2 * 1024 * 1024);
    const start = performance.now();
    const safe = redactRun(validateRun(run));
    const elapsed = performance.now() - start;
    assert.equal(safe.redactionCount, 0);
    assert.equal(safe.run.steps[19].content, content);
    assert.ok(elapsed < 1500, `20 maximum-size fields, suffix=${JSON.stringify(suffix)}: ${elapsed.toFixed(1)}ms exceeds 1500ms`);
    console.log(`Adversarial ~2 MB validation/redaction suffix=${JSON.stringify(suffix)}: ${elapsed.toFixed(1)}ms`);
  }
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
