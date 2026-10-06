export const examples = [
  {name: 'Explore and recover', run: {schema_version: 1, run_id: 'example-exploration', task: 'Find the project configuration, recover from a missing path, and summarize the result.', status: 'completed', steps: [
    {id: '1', kind: 'task', content: 'Find the project configuration and report the runtime.'},
    {id: '2', kind: 'tool_call', tool: 'read_file', call_id: 'a', content: '{"path":"settings.json"}'},
    {id: '3', kind: 'tool_result', call_id: 'a', status: 'error', content: 'File not found: settings.json'},
    {id: '4', kind: 'assistant', content: 'The guessed path is absent. List the directory to locate the actual configuration.'},
    {id: '5', kind: 'tool_call', tool: 'list_files', call_id: 'b', content: '{"path":"."}'},
    {id: '6', kind: 'tool_result', call_id: 'b', status: 'ok', content: 'README.md\npackage.json'},
    {id: '7', kind: 'tool_call', tool: 'read_file', call_id: 'c', content: '{"path":"package.json"}'},
    {id: '8', kind: 'tool_result', call_id: 'c', status: 'ok', content: '{"engines":{"node":">=20"}}'},
    {id: '9', kind: 'assistant', content: 'The package configuration specifies Node.js 20 or later. The earlier missing path was a recoverable exploratory attempt.'}
  ]}},
  {name: 'Repeated calls and missing evidence', run: {schema_version: 1, run_id: 'example-review', task: 'Review a completed search run with retries and an incomplete tool record.', status: 'completed', steps: [
    {id: '1', kind: 'task', content: 'Find a document about release readiness.'},
    {id: '2', kind: 'tool_call', tool: 'search', call_id: 'a', content: 'release readiness'},
    {id: '3', kind: 'tool_result', call_id: 'a', status: 'ok', content: 'No matches.'},
    {id: '4', kind: 'tool_call', tool: 'search', call_id: 'b', content: 'release readiness'},
    {id: '5', kind: 'tool_result', call_id: 'b', status: 'ok', content: 'No matches.'},
    {id: '6', kind: 'tool_call', tool: 'search', call_id: 'c', content: 'release readiness'},
    {id: '7', kind: 'tool_result', call_id: 'unknown', content: 'Found draft notes.'},
    {id: '8', kind: 'assistant', content: 'The run is finished. A reviewer should check whether a result was omitted from the export.'}
  ]}},
  {name: 'Clean completion', run: {schema_version: 1, run_id: 'example-clean', task: 'List project files.', status: 'completed', steps: [
    {id: '1', kind: 'tool_call', tool: 'list_files', call_id: 'c1', content: '{"path":"."}'},
    {id: '2', kind: 'tool_result', call_id: 'c1', status: 'ok', content: 'README.md\npackage.json'},
    {id: '3', kind: 'assistant', content: 'Found README.md and package.json.'}
  ]}}
];
