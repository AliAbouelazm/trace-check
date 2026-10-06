// Rules only. Raw input stays in private pipes; stdout contains positions only.
import readline from 'node:readline';
import {analyzeRun} from '../web/core.js';
for await (const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})) {
  try {
    const run=JSON.parse(line), byId=new Map(run.steps.map(s=>[s.id,s]));
    // Preserve the archived mapping, including last-call-id wins.
    const calls=new Map(run.steps.filter(s=>s.kind==='tool_call').map(s=>[s.call_id,Number(s.id.slice(1).split('-')[0])]));
    const flagged=new Set();
    for (const flag of analyzeRun(run)) {
      const step=byId.get(flag.step_id);
      const index=step.kind==='tool_result'?calls.get(step.call_id):['assistant','tool_call'].includes(step.kind)?Number(step.id.slice(1).split('-')[0]):undefined;
      if(index!==undefined)flagged.add(index);
    }
    console.log(JSON.stringify([...flagged]));
  } catch { console.log(JSON.stringify({error:'Rules rejected input'})); }
}
