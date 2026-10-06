// Handwritten synthetic walkthrough, not a benchmark or accuracy claim.
const steps = [
  {id:'u',kind:'task',content:'Inspect the configuration and run the tests.'},
  {id:'a',kind:'assistant',content:'I will inspect the configuration before testing.'},
  {id:'c',kind:'tool_call',tool:'read_file',call_id:'c1',content:'{"path":"config.json"}'},
  {id:'t',kind:'tool_result',tool:'read_file',call_id:'c1',status:'error',content:'File not found.'},
  {id:'b',kind:'assistant',content:'The request failed. I will retry the same command.'},
  {id:'d',kind:'tool_call',tool:'read_file',call_id:'c2',content:'{"path":"config.json"}'},
  {id:'v',kind:'tool_result',tool:'read_file',call_id:'c2',status:'error',content:'File not found.'},
  {id:'z',kind:'assistant',content:'I cannot verify the configuration from these results.'}
];
export const demoEnvelope = {envelope_version:1,run:{schema_version:1,run_id:'Synthetic ML walkthrough',task:'A handwritten failed file lookup. No accuracy claim.',status:'completed',steps},messages:[
  {role:'user',step_ids:['u']},{role:'assistant',step_ids:['a','c']},{role:'tool',step_ids:['t']},
  {role:'assistant',step_ids:['b','d']},{role:'tool',step_ids:['v']},{role:'assistant',step_ids:['z']}
]};
