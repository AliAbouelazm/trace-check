import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateRun,analyzeRun,redactRun,makeReport,REPORT_VERSION} from '../web/core.js';
const parallel=JSON.parse(readFileSync(new URL('./fixtures/parallel-tools.json',import.meta.url)));
test('multiple calls from one assistant action match independently despite reversed results',()=>{
  assert.equal(validateRun(parallel).steps.length,7);
  assert.deepEqual(analyzeRun(parallel),[]);
  const incomplete=structuredClone(parallel);incomplete.steps.splice(5,1);
  const flags=analyzeRun(incomplete);
  assert.deepEqual(flags.map(f=>[f.rule,f.step_id]),[['missing_result','m1-call0']]);
  assert.match(flags[0].uncertainty,/log may be incomplete/);
});
test('reported tool errors retain uncertainty and never mark a successful parallel call as causal',()=>{
  const run=structuredClone(parallel);run.steps[4].status='error';run.steps[4].content='Request failed; another call completed.';
  const flags=analyzeRun(run);
  assert.deepEqual(flags.map(f=>f.step_id),['m2']);
  assert.match(flags[0].title,/possible error/);
  assert.match(flags[0].uncertainty,/benign/);
  assert.equal(flags[0].severity,'review');
});
test('versioned report retains full redacted run and offers actionable reimport guidance',()=>{
  const run=redactRun(parallel).run, flags=analyzeRun(run), report=makeReport(run,flags,0);
  const schema=JSON.parse(readFileSync(new URL('../docs/report-schema.json',import.meta.url)));
  assert.equal(report.report_version,REPORT_VERSION);
  assert.equal(report.report_version,schema.properties.report_version.const);
  assert.deepEqual(Object.keys(report).sort(),schema.required.slice().sort());
  assert.deepEqual(validateRun(report.run),run);
  assert.equal(report.run.steps.length,7);
  assert.ok(Number.isFinite(Date.parse(report.generated_at)));
  assert.match(report.review_method,/Structural rules only/);
  assert.match(report.limitations,/not causal diagnoses/);
  assert.throws(()=>validateRun(report),/save its run object/);
});
