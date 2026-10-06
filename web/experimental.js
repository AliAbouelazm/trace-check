// Strict grouping and frozen scorer for optional manual review. No training.
import {MAX_FILE_BYTES, validateRun} from './core.js';
export const MODEL_BYTES = 2 * 1024 * 1024;
export const MAX_FEATURES = 20000;
const encoder = new TextEncoder();
function object(value, fields) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length !== fields.length || fields.some(key => !Object.hasOwn(value, key))) throw new Error('Unsupported experimental object shape.');
}
function parse(text, limit) {
  if (typeof text !== 'string' || text.length > limit || encoder.encode(text).length > limit) throw new Error('Experimental JSON exceeds byte limit.');
  return JSON.parse(text);
}
export function parseEnvelope(text) {
  const value = parse(text, MAX_FILE_BYTES);
  object(value, ['envelope_version', 'run', 'messages']);
  if (value.envelope_version !== 1) throw new Error('Unsupported envelope version.');
  const run = validateRun(value.run);
  if (!Array.isArray(value.messages) || !value.messages.length || value.messages.length > 2000) throw new Error('Expected 1 to 2000 original message groups.');
  let position = 0;
  const groups = value.messages.map(group => {
    object(group, ['role', 'step_ids']);
    if (!['user', 'assistant', 'tool', 'excluded'].includes(group.role) || !Array.isArray(group.step_ids)) throw new Error('Invalid original message group.');
    if (group.role === 'excluded') {
      if (group.step_ids.length) throw new Error('Excluded message must have no timeline text.');
      return {role: 'excluded', steps: []};
    }
    if (!group.step_ids.length || (group.role !== 'assistant' && group.step_ids.length !== 1)) throw new Error('Invalid message mapping length.');
    const steps = group.step_ids.map((id, i) => {
      const step = run.steps[position++];
      const expected = i ? 'tool_call' : {user:'task', assistant:'assistant', tool:'tool_result'}[group.role];
      if (!step || id !== step.id || step.kind !== expected || (i && !step.tool)) throw new Error('Mapping must cover ordered steps once with matching kinds.');
      return step;
    });
    return {role: group.role, steps};
  });
  if (position !== run.steps.length || !groups.some(group => group.role === 'assistant')) throw new Error('Incomplete original message mapping.');
  return {run, groups};
}
const codepoints = (text, start, end) => Array.from(text).slice(start, end).join('');
export function feature(envelope, index) {
  const groups = envelope.groups;
  const last = groups.findLastIndex(group => group.role === 'assistant');
  if (!Number.isInteger(index) || index < 0 || index >= last || groups[index]?.role !== 'assistant') throw new Error('Only nonfinal original assistant messages may be scored.');
  const parts = [];
  for (const group of groups.slice(Math.max(0, index - 2), index + 1)) {
    if (group.role === 'excluded') continue;
    const [main, ...calls] = group.steps;
    const content = main.content.replace(/<an[sſ]wer>.*?<\/an[sſ]wer>/gis, '[answer omitted]');
    parts.push(group.role + ' ' + codepoints(content, 0, 4000));
    for (const call of calls) parts.push(call.tool + ' ' + codepoints(call.content, 0, 4000));
  }
  return codepoints(parts.join('\n'), -12000);
}
export function parseArtifact(text) {
  const a = parse(text, MODEL_BYTES);
  object(a, ['artifact_version','feature_contract','tokenizer','classes','vocabulary','idf','coefficients','intercept','threshold','provenance']);
  if (a.artifact_version !== 1 || a.feature_contract !== 'original-messages-v1' || a.tokenizer !== 'sklearn-ascii-v1' || JSON.stringify(a.classes) !== '[-1,0,1]') throw new Error('Unsupported model contract.');
  if (![.5,.6,.7,.8,.9,.95].includes(a.threshold)) throw new Error('Unsupported threshold.');
  const n = a.vocabulary?.length;
  if (!Array.isArray(a.vocabulary) || !n || n > MAX_FEATURES || new Set(a.vocabulary).size !== n || a.vocabulary.some(term => typeof term !== 'string' || !term.length || term.length > 200)) throw new Error('Invalid vocabulary.');
  const vector = (v, size, low, high) => Array.isArray(v) && v.length === size && v.every(x => typeof x === 'number' && Number.isFinite(x) && x >= low && x <= high);
  if (!vector(a.idf,n,1,100) || !vector(a.intercept,3,-1000,1000) || !Array.isArray(a.coefficients) || a.coefficients.length !== 3 || !a.coefficients.every(row => vector(row,n,-1000,1000))) throw new Error('Invalid finite model dimensions or values.');
  object(a.provenance, ['kind','source_hashes','split_sha256']);
  const hash = s => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s);
  if (!['synthetic','train-validation'].includes(a.provenance.kind) || !Array.isArray(a.provenance.source_hashes) || a.provenance.source_hashes.length > 4 || !a.provenance.source_hashes.every(hash)) throw new Error('Invalid provenance.');
  if (a.provenance.kind === 'synthetic' ? a.provenance.source_hashes.length || a.provenance.split_sha256 !== null : !a.provenance.source_hashes.length || !hash(a.provenance.split_sha256)) throw new Error('Invalid split provenance.');
  return {...a, lookup: new Map(a.vocabulary.map((term,i) => [term,i]))};
}
export function score(model, text) {
  if (typeof text !== 'string' || Array.from(text).length > 12000) throw new Error('Feature exceeds contract.');
  // Conservative support boundary: Python/JS Unicode word and case tables can
  // differ. Preserve Unicode features, but abstain rather than approximate them.
  if (/[^\x00-\x7f]/.test(text)) return {abstention:'unsupported-unicode', scores:null, suggestion:false};
  const tokens = text.toLowerCase().match(/[a-z0-9_]{2,}/g) || [];
  const counts = new Map();
  const add = term => { const i = model.lookup.get(term); if (i !== undefined) counts.set(i, (counts.get(i) || 0) + 1); };
  tokens.forEach(add);
  for (let i = 1; i < tokens.length; i++) add(tokens[i-1] + ' ' + tokens[i]);
  if (!counts.size) return {abstention:'no-known-features', scores:null, suggestion:false};
  const weighted = [...counts].sort((a,b) => a[0]-b[0]).map(([i,n]) => [i,(1 + Math.log(n))*model.idf[i]]);
  const norm = Math.sqrt(weighted.reduce((total,[,v]) => total + v*v,0));
  const logits = model.coefficients.map((row,k) => weighted.reduce((total,[i,v]) => total + row[i]*v/norm, model.intercept[k]));
  const maximum = Math.max(...logits);
  const exp = logits.map(x => Math.exp(x-maximum)); const total = exp.reduce((a,b) => a+b,0);
  const scores = exp.map(x => x/total);
  const boundary = Math.abs(scores[0]-model.threshold) <= 1e-6;
  return {scores, suggestion: !boundary && scores[0] > model.threshold, abstention: boundary ? 'threshold-ambiguity' : scores[0] < model.threshold ? 'below-threshold' : null};
}
