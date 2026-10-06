export const REPORT_VERSION = 1;
export const MAX_FILE_BYTES = 2 * 1024 * 1024;
export const KINDS = ['task', 'assistant', 'tool_call', 'tool_result'];
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function keys(value, allowed, path) {
  if (!isObject(value)) throw new Error(`${path} must be an object.`);
  for (const key of Object.keys(value)) if (!allowed.includes(key)) throw new Error(`${path}: unknown field. Remove labels, ground truth, answers, and other unsupported fields.`);
}
function str(value, name, max, empty = false) {
  if (typeof value !== 'string' || (!empty && !value.trim()) || value.length > max) throw new Error(`${name} must be ${empty ? 'a' : 'a nonempty'} string of at most ${max} characters.`);
}
export function validateRun(value) {
  if (isObject(value) && Object.hasOwn(value, 'report_version')) throw new Error('To review an exported report, save its run object as a separate JSON file and import it. Download sample shows the required run format.');
  keys(value, ['schema_version', 'run_id', 'task', 'status', 'steps'], 'Run');
  if (value.schema_version !== 1) throw new Error('schema_version must be 1.');
  if (value.status !== 'completed') throw new Error('Only completed runs are supported.');
  str(value.run_id, 'run_id', 200); str(value.task, 'task', 20000);
  if (!Array.isArray(value.steps) || value.steps.length < 1 || value.steps.length > 2000) throw new Error('steps must contain 1 to 2000 entries.');
  const ids = new Set();
  for (const [i, step] of value.steps.entries()) {
    const path = `Step ${i + 1}`;
    keys(step, ['id', 'kind', 'content', 'tool', 'call_id', 'status'], path);
    str(step.id, `${path} id`, 200); str(step.content, `${path} content`, 100000, true);
    if (ids.has(step.id)) throw new Error(`${path}: duplicate step id.`); ids.add(step.id);
    if (!KINDS.includes(step.kind)) throw new Error(`${path}: unsupported kind.`);
    for (const key of ['tool', 'call_id']) if (step[key] !== undefined) str(step[key], `${path} ${key}`, 200);
    if (step.status !== undefined && !['ok', 'error'].includes(step.status)) throw new Error(`${path}: status must be ok or error.`);
  }
  return JSON.parse(JSON.stringify(value));
}
export function analyzeRun(run) {
  const flags = [];
  const add = (step, rule, title, evidence, uncertainty, severity = 'review') => flags.push({id: `${rule}:${step.id}`, rule, step_id: step.id, severity, title, evidence, uncertainty});
  const pending = new Map(), repeats = new Map();
  for (const step of run.steps) {
    if (step.kind === 'tool_call') {
      if (step.call_id) {
        const queue = pending.get(step.call_id) || []; queue.push(step); pending.set(step.call_id, queue);
      }
      const signature = JSON.stringify([step.tool || '', step.content]);
      const group = repeats.get(signature) || []; group.push(step); repeats.set(signature, group);
      if (group.length === 3) add(step, 'repeated_call', 'Repeated identical tool call', `The same tool and input appear at steps ${group.map(s => s.id).join(', ')}.`, 'Retries, polling, or deliberate verification can be valid. Repetition alone does not establish a mistake.');
    }
    if (step.kind === 'tool_result') {
      if (step.call_id) {
        const queue = pending.get(step.call_id);
        if (!queue?.length) add(step, 'unmatched_result', 'Result without preceding matching call', `Result references call_id ${step.call_id}, with no unmatched preceding call.`, 'The export may omit calls or use a different identifier convention.');
        else queue.shift();
      }
      if (step.status === 'error' || /(?:\b(?:error|exception|traceback|failed|failure)\b|permission denied|not found)/i.test(step.content)) add(step, 'tool_error', 'Tool result reports a possible error', step.status === 'error' ? 'The result has status "error".' : `Matched error-like text: ${redactRun(step.content).run.match(/.{0,45}(?:error|exception|traceback|failed|failure|permission denied|not found).{0,45}/i)?.[0] || 'error term'}`, 'Expected failures, quoted error text, and useful exploration can be benign. Review the surrounding steps.');
    }
  }
  for (const [callId, queue] of pending) for (const step of queue) add(step, 'missing_result', 'Call without matching result', `No later tool result matches call_id ${callId}.`, 'The log may be incomplete or this tool may not emit a result.');
  return flags;
}
export function redactRun(run) {
  let redactionCount = 0;
  const redact = value => value
    // Consume complete quoted values first, including escaped characters and
    // literal newlines. An unterminated quoted value is redacted to end of text.
    // The unquoted alternative cannot begin with a quote, so it cannot expose
    // the suffix of a quoted secret. This is text matching, never evaluation.
    .replace(/\b((?:api[_ -]?key|password|secret|access[_ -]?token|authorization)["']?\s*[=:]\s*)("(?:\\(?:[\s\S]|$)|[^"\\])*(?:"|$)|'(?:\\(?:[\s\S]|$)|[^'\\])*(?:'|$)|(?:bearer\s+)?[^\s"',;}]+)/gi, (_, prefix, value) => {
      redactionCount++;
      const quote = value[0] === '"' || value[0] === "'" ? value[0] : '';
      return `${prefix}${quote}[REDACTED]${quote && value.endsWith(quote) ? quote : ''}`;
    })
    // Scan disjoint maximal candidates once. Validate only bounded candidates;
    // retrying an email pattern at every dot boundary is quadratic on long logs.
    .replace(/[A-Z0-9._%+@-]+/gi, candidate => {
      if (candidate.length > 512) return candidate;
      const address = candidate.replace(/\.+$/, '');
      if (address.length > 254 || !/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(address)) return candidate;
      redactionCount++; return '[REDACTED EMAIL]' + candidate.slice(address.length);
    })
    .replace(/\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|AKIA[A-Z0-9]{16})\b/g, () => { redactionCount++; return '[REDACTED TOKEN]'; });
  // Preserve internal identifiers for matching, but redact them for display/export as well.
  const map = value => typeof value === 'string' ? redact(value) : Array.isArray(value) ? value.map(map) : isObject(value) ? Object.fromEntries(Object.entries(value).map(([key, item]) => [key, map(item)])) : value;
  const safe = map(run);
  if (isObject(run) && Array.isArray(run.steps) && run.steps.some((step, i) => step.id !== safe.steps[i].id || step.call_id !== safe.steps[i].call_id)) {
    const calls = new Map();
    run.steps.forEach((step, i) => {
      safe.steps[i].id = `step-${i + 1}`;
      if (step.call_id !== undefined) {
        if (!calls.has(step.call_id)) calls.set(step.call_id, `call-${calls.size + 1}`);
        safe.steps[i].call_id = calls.get(step.call_id);
      }
    });
  }
  return {run: safe, redactionCount};
}
export function makeReport(run, flags, redactionCount) {
  return {report_version: REPORT_VERSION, generated_at: new Date().toISOString(), review_method: 'Structural rules only. No trained model or model confidence is presented.', limitations: 'Flags are observations for review, not causal diagnoses. Rules can miss semantic mistakes and flag benign exploration. Redaction is best effort.', redaction_count: redactionCount, run, flags};
}
