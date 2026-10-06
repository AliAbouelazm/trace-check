import {MAX_FILE_BYTES, validateRun, analyzeRun, redactRun, makeReport} from './core.js';
import {parseEnvelope} from './experimental.js';
import {reviewBundled} from './experimental-client.js';
import {demoEnvelope} from './review-demo.js';
import {examples} from './examples.js';
const $ = id => document.getElementById(id);
let originalEnvelope = null, reviewController = null, reviewNotes = null;
let current = null, flags = [], redactions = 0, loadVersion = 0;
function node(tag, text, className) { const result = document.createElement(tag); if (text !== undefined) result.textContent = text; if (className) result.className = className; return result; }
function showError(message) { $('load-status').textContent = ''; $('error-message').textContent = message; $('error').hidden = false; $('error').focus(); }
function clear() { resetML(); originalEnvelope = null; loadVersion++; current = null; flags = []; redactions = 0; $('timeline').replaceChildren(); $('run-title').textContent = ''; $('task').textContent = ''; $('review').hidden = true; $('error').hidden = true; $('file').value = ''; $('search').value = ''; $('kind').value = ''; $('flagged').checked = false; $('load-status').textContent = ''; }
function load(value) {
  resetML();
  originalEnvelope = value?.envelope_version === 1 ? JSON.stringify(value) : null;
  const validated = originalEnvelope ? parseEnvelope(originalEnvelope).run : validateRun(value);
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
  $('search').value = ''; $('kind').value = ''; $('flagged').checked = false;
  $('review-note').textContent = flags.length ? 'Observations request review; they do not prove a mistake or its cause.' : 'No structural rules matched. This does not establish that the run is correct; semantic mistakes can be missed.';
  $('ml-enable').disabled = !originalEnvelope;
  $('ml-status').textContent = originalEnvelope ? 'Off for this run. Original message grouping is available.' : 'Unavailable: this run lacks explicit original message grouping. Rules remain available.';
  render(); $('run-title').focus(); $('load-status').textContent = `Loaded ${current.steps.length} steps with ${flags.length} review observations. Rules only.`;
}
function render() {
  if (!current) return;
  const query = $('search').value.toLowerCase(), kind = $('kind').value;
  const matching = current.steps.filter(step => (!kind || step.kind === kind) && (!$('flagged').checked || step._flags.length) && [step.id, step.content, step.tool || '', ...step._flags.map(flag => flag.title)].join(' ').toLowerCase().includes(query));
  const fragment = document.createDocumentFragment();
  for (const step of matching) {
    const article = node('article', undefined, `step ${step._flags.length ? 'has-flag' : ''}`);
    article.id = `timeline-step-${current.steps.indexOf(step)}`; article.tabIndex = -1;
    const head = node('div', undefined, 'step-head'); head.append(node('span', step.kind.replace('_', ' '), 'badge'), node('span', `Step ${step.id}`, 'step-id'));
    if (step.tool) head.append(node('strong', step.tool)); if (step.call_id) head.append(node('span', `Call ${step.call_id}`, 'step-id'));
    article.append(head, node('pre', step.content || '(empty content)', 'content'));
    for (const flag of step._flags) { const box = node('div', undefined, 'flag'); box.append(node('strong', `Review · ${flag.title}`), node('p', flag.evidence), node('p', flag.uncertainty, 'uncertainty')); article.append(box); }
    fragment.append(article);
  }
  if (!matching.length) fragment.append(node('p', 'No steps match these filters. Clear filters to show the full run.', 'empty'));
  $('reset-filters').hidden = !query && !kind && !$('flagged').checked;
  $('timeline').replaceChildren(fragment); $('visible-count').textContent = `${matching.length} of ${current.steps.length} shown`;
}
function download(value, filename) { const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], {type: 'application/json'})); const link = node('a'); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
$('file').addEventListener('change', async event => { const file = event.target.files[0]; if (!file) return; clear(); $('load-status').textContent = 'Reading JSON locally…'; const version = loadVersion; try { if (file.size > MAX_FILE_BYTES) throw new Error('File is too large. Maximum size is 2 MiB.'); const raw = await file.text(); if (version !== loadVersion) return; let parsed; try { parsed = JSON.parse(raw); } catch { throw new Error('This file is not valid JSON. Use the downloadable sample format.'); } load(parsed); } catch (error) { if (version === loadVersion) showError(error.message); } });
for (const example of examples) { const button = node('button', example.name); button.addEventListener('click', () => { clear(); load(example.run); }); $('examples').append(button); }
$('sample').addEventListener('click', () => download(examples[0].run, 'trace-check-sample.json'));
$('export').addEventListener('click', () => { if (!current) return; const run = {...current, steps: current.steps.map(({_flags, ...step}) => step)}; download(makeReport(run, flags, redactions), 'trace-check-report.json'); });
$('choose').addEventListener('click', () => $('file').click());
$('retry').addEventListener('click', () => $('file').click());
$('clear').addEventListener('click', () => { clear(); $('load-status').textContent = 'Run cleared from this tab.'; $('choose').focus(); });
$('reset-filters').addEventListener('click', () => { $('search').value = ''; $('kind').value = ''; $('flagged').checked = false; render(); $('search').focus(); });
for (const id of ['search', 'kind', 'flagged']) $(id).addEventListener('input', render);

function resetML() {
  reviewController?.abort(); reviewController = null; reviewNotes = null;
  $('ml-enable').checked = false; $('ml-cancel').hidden = true; $('ml-export').disabled = true;
  $('ml-results').replaceChildren(); $('ml-status').textContent = 'Off for this run.';
}
$('ml-enable').addEventListener('change', async () => {
  if (!$('ml-enable').checked) { resetML(); return; }
  if (!originalEnvelope) return;
  const controller = new AbortController(); reviewController = controller;
  $('ml-cancel').hidden = false; $('ml-results').replaceChildren();
  $('ml-status').textContent = 'Starting local review…';
  try {
    const result = await reviewBundled(originalEnvelope, {signal:controller.signal,onProgress:progress => {
      if (reviewController === controller) $('ml-status').textContent = progress.stage;
    }});
    if (reviewController !== controller) return;
    reviewNotes = result; $('ml-export').disabled = false;
    const c = result.coverage, suggestions = result.results.filter(r => r.suggestion);
    $('ml-status').textContent = `${suggestions.length} suggestions · ${c.scored_actions}/${c.eligible_actions} eligible actions scored · ${c.unsupported_actions} unsupported · ${c.truncated_actions} truncated · ${c.final_assistant_excluded} final assistant excluded. No suggestion is not a clean bill of health.`;
    for (const r of result.results) {
      const card = node('article', undefined, r.suggestion ? 'ml-card suggested' : 'ml-card');
      const title = r.suggestion ? 'Review suggestion' : r.abstention === 'threshold-ambiguity' ? 'Boundary abstention' : r.scores ? 'Below review cutoff' : 'Abstained';
      card.append(node('strong', `${title} · original message ${r.message_index + 1}`));
      card.append(node('p', r.scores ? `Uncalibrated decision score ${r.scores[0].toFixed(4)} · fixed cutoff 0.70. This is not confidence or probability of a mistake.` : `Unsupported: ${r.abstention}.`));
      card.append(node('p', 'Observed log context only; the model does not supply a causal explanation.', 'privacy'));
      card.append(node('pre', current.steps[r.step_index].content || '(empty content)', 'content'));
      if (r.truncation.field_characters_removed || r.truncation.joined_characters_removed) card.append(node('p', `Input truncated: ${r.truncation.field_characters_removed} field characters and ${r.truncation.joined_characters_removed} joined characters removed. Tool-call text may be lost.`));
      const link = node('button','View in timeline');
      link.addEventListener('click', () => { $('search').value=''; $('kind').value=''; $('flagged').checked=false; render(); const target=$(`timeline-step-${r.step_index}`); target.scrollIntoView({block:'center'}); target.focus(); });
      card.append(link); $('ml-results').append(card);
    }
  } catch (error) {
    if (reviewController === controller) { $('ml-status').textContent = error.message; $('ml-enable').checked = false; }
  } finally { if (reviewController === controller) { reviewController = null; $('ml-cancel').hidden = true; } }
});
$('ml-cancel').addEventListener('click', () => { resetML(); $('ml-status').textContent = 'Experimental review cancelled. Rules remain available.'; });
$('ml-export').addEventListener('click', () => {
  if (!current || !reviewNotes) return;
  download({review_notes_version:1,run:{...current,steps:current.steps.map(({_flags,...step})=>step)},...reviewNotes},'trace-check-review-notes.json');
});
$('ml-demo').addEventListener('click', () => { clear(); load(demoEnvelope); });
