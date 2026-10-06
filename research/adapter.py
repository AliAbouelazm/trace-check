"""Explicit allowlist adapter. No dataset code is imported or executed."""
import argparse
import json
import re
import subprocess
from pathlib import Path


def text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def adapt(row, subset='dataset', exclude_final=False):
    messages = row['messages']
    last = max((i for i, m in enumerate(messages) if m.get('role') == 'assistant'), default=-1)
    steps = []
    for i, m in enumerate(messages):
        if exclude_final and i >= last:
            break
        role = m.get('role')
        if role == 'system':
            continue  # Often huge tool specifications, not a user task.
        if role not in ('user', 'assistant', 'tool'):
            raise ValueError(f'Unsupported message role at {i}')
        content = text(m.get('content') or '')
        if exclude_final:
            content = re.sub(r'<answer>.*?</answer>', '[answer omitted]', content, flags=re.S | re.I)
        step = {'id': f'm{i}', 'kind': {'user': 'task', 'assistant': 'assistant', 'tool': 'tool_result'}[role], 'content': content}
        if role == 'tool':
            if m.get('name'): step['tool'] = str(m['name'])
            if m.get('tool_call_id'): step['call_id'] = str(m['tool_call_id'])
        steps.append(step)
        if role == 'assistant':
            for j, call in enumerate(m.get('tool_calls') or []):
                f = call['function']
                steps.append({'id': f'm{i}-call{j}', 'kind': 'tool_call', 'content': text(f.get('arguments', '')), 'tool': str(f['name']), 'call_id': str(call.get('id') or f'm{i}-call{j}')})
    return {'schema_version': 1, 'run_id': f'{subset}-{row["query_index"]}-{row["sample_index"]}', 'task': text(row.get('question') or 'Conversation task'), 'status': 'completed', 'steps': steps}


def feature(row, index):
    """Prefix only, allowlisted text; no final assistant, outcomes, IDs or labels."""
    messages = row['messages']
    last = max(i for i, m in enumerate(messages) if m.get('role') == 'assistant')
    if index >= last:
        raise ValueError('Final assistant message excluded from research model')
    parts = []
    for m in messages[max(0, index - 2):index + 1]:
        if m.get('role') not in ('assistant', 'user', 'tool'): continue
        content = re.sub(r'<answer>.*?</answer>', '[answer omitted]', text(m.get('content') or ''), flags=re.S | re.I)
        parts.append(m['role'] + ' ' + content[:4000])
        for c in m.get('tool_calls') or []:
            f = c['function']
            parts.append(str(f['name']) + ' ' + text(f.get('arguments', ''))[:4000])
    return '\n'.join(parts)[-12000:]


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Convert one AgentProcessBench JSONL row into Trace Check JSON locally.')
    p.add_argument('input', type=Path); p.add_argument('output', type=Path); p.add_argument('--row', type=int, default=0)
    a = p.parse_args()
    if a.row < 0: p.error('--row must be nonnegative')
    with a.input.open() as f:
        for i, line in enumerate(f):
            if i == a.row:
                payload = json.dumps(adapt(json.loads(line), a.input.stem), ensure_ascii=False, indent=2)
                if len(payload.encode('utf-8')) > 2 * 1024 * 1024:
                    p.error('Converted run exceeds the 2 MiB import limit. No output written; select another run.')
                check = subprocess.run(['node', '--input-type=module', '-e', "import {validateRun} from './web/core.js'; let s=''; for await(const c of process.stdin)s+=c; try{validateRun(JSON.parse(s))}catch(e){console.error(e.message);process.exit(1)}"], input=payload, text=True, capture_output=True, cwd=Path(__file__).resolve().parent.parent)
                if check.returncode: p.error('Converted run does not fit import schema: ' + check.stderr.strip())
                a.output.write_text(payload)
                break
        else: p.error('Row not found')
