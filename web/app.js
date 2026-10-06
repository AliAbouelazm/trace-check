import {MAX_FILE_BYTES, validateRun, analyzeRun, redactRun, makeReport} from './core.js';
import {examples} from './examples.js';
const $ = id => document.getElementById(id);
let current = null, flags = [], redactions = 0, loadVersion = 0;
function node(tag, text, className) { const result = document.createElement(tag); if (text !== undefined) result.textContent = text; if (className) result.className = className; return result; }
function showError(message) { $('error').textContent = message; $('error').hidden = false; }
function clear() { loadVersion++; current = null; flags = []; redactions = 0; $('timeline').replaceChildren(); $('run-title').textContent = ''; $('task').textContent = ''; $('review').hidden = true; $('error').hidden = true; $('file').value = ''; $('search').value = ''; $('kind').value = ''; $('flagged').checked = false; }
function load(value) {
  const validated = validateRun(value);
  // Analyze before redaction so distinct tool inputs/identifiers cannot collapse into false matches.
  const observations = analyzeRun(validated);
  const safe = redactRun(validated);
  const safeFlags = redactRun(observations).run;
  safeFlags.forEach((flag, i) => { const index = validated.steps.findIndex(step => step.id === observations[i].step_id); flag.step_id = safe.run.steps[index].id; flag.id = `${flag.rule}:${flag.step_id}`; });
  current = safe.run; flags = safeFlags; redactions = safe.redactionCount;
  // Match flags by position, because redacted IDs can collide.
  current.steps.forEach((step, i) => { step._flags = observations.map((flag, index) => flag.step_id === validated.steps[i].id ? safeFlags[index] : null).filter(Boolean); });
  $('error').hidden = true; $('review').hidden = false; $('run-title').textContent = current.run_id; $('task').textContent = current.task;
  $('steps-count').textContent = current.steps.length; $('flags-count').textContent = flags.length; $('redactions-count').textContent = redactions;
  $('search').value = ''; $('kind').value = ''; $('flagged').checked = false; render();
}
function render() {
  if (!current) return;
  const query = $('search').value.toLowerCase(), kind = $('kind').value;
  const matching = current.steps.filter(step => (!kind || step.kind === kind) && (!$('flagged').checked || step._flags.length) && [step.id, step.content, step.tool || '', ...step._flags.map(flag => flag.title)].join(' ').toLowerCase().includes(query));
  const fragment = document.createDocumentFragment();
  for (const step of matching) {
    const article = node('article', undefined, `step ${step._flags.length ? 'has-flag' : ''}`);
    const head = node('div', undefined, 'step-head'); head.append(node('span', step.kind.replace('_', ' '), 'badge'), node('span', `Step ${step.id}`, 'step-id'));
    if (step.tool) head.append(node('strong', step.tool)); if (step.call_id) head.append(node('span', `Call ${step.call_id}`, 'step-id'));
    article.append(head, node('pre', step.content || '(empty content)', 'content'));
    for (const flag of step._flags) { const box = node('div', undefined, 'flag'); box.append(node('strong', `Review · ${flag.title}`), node('p', flag.evidence), node('p', flag.uncertainty, 'uncertainty')); article.append(box); }
    fragment.append(article);
  }
  if (!matching.length) fragment.append(node('p', 'No steps match these filters.', 'empty'));
  $('timeline').replaceChildren(fragment); $('visible-count').textContent = `${matching.length} of ${current.steps.length} shown`;
}
function download(value, filename) { const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], {type: 'application/json'})); const link = node('a'); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
$('file').addEventListener('change', async event => { const file = event.target.files[0]; if (!file) return; clear(); const version = loadVersion; try { if (file.size > MAX_FILE_BYTES) throw new Error('File is too large. Maximum size is 2 MiB.'); const raw = await file.text(); if (version !== loadVersion) return; let parsed; try { parsed = JSON.parse(raw); } catch { throw new Error('This file is not valid JSON. Use the downloadable sample format.'); } load(parsed); } catch (error) { if (version === loadVersion) showError(error.message); } });
for (const example of examples) { const button = node('button', example.name); button.addEventListener('click', () => { clear(); load(example.run); }); $('examples').append(button); }
$('sample').addEventListener('click', () => download(examples[0].run, 'trace-check-sample.json'));
$('export').addEventListener('click', () => { if (!current) return; const run = {...current, steps: current.steps.map(({_flags, ...step}) => step)}; download(makeReport(run, flags, redactions), 'trace-check-report.json'); });
$('clear').addEventListener('click', clear);
for (const id of ['search', 'kind', 'flagged']) $(id).addEventListener('input', render);
