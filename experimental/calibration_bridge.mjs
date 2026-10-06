// Private subprocess bridge for the reviewed calibration driver, not app input.
import readline from 'node:readline';
import {createHash} from 'node:crypto';
import {analyzeRun} from '../web/core.js';
import {parseEnvelope,parseArtifact,feature,score} from '../web/experimental.js';
let model=null;
for await(const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})) {
  try {
    const request=JSON.parse(line);
    if(request.artifactJSON !== undefined){model=parseArtifact(request.artifactJSON);console.log(JSON.stringify({accepted:true}));continue;}
    if(request.text !== undefined){if(!model)throw new Error();console.log(JSON.stringify(score(model,request.text)));continue;}
    let compatible=false, hashes={};
    if(request.envelopeJSON !== null){
      try {
        const envelope=parseEnvelope(request.envelopeJSON);
        hashes=Object.fromEntries(request.indices.map(i=>[i,createHash('sha256').update(feature(envelope,i)).digest('hex')]));
        compatible=true;
      }catch{ /* Unsupported canonical envelopes abstain without dropping labels. */ }
    }
    const flagged=new Set();
    if(request.rule_run){
      const run=request.rule_run,byId=new Map(run.steps.map(s=>[s.id,s]));
      // Same target mapping as frozen evaluate.py, including last-call-id wins.
      const calls=new Map(run.steps.filter(s=>s.kind==='tool_call').map(s=>[s.call_id,Number(s.id.slice(1).split('-')[0])]));
      for(const flag of analyzeRun(run)){
        const step=byId.get(flag.step_id);
        const index=step.kind==='tool_result'?calls.get(step.call_id):['assistant','tool_call'].includes(step.kind)?Number(step.id.slice(1).split('-')[0]):undefined;
        if(index!==undefined)flagged.add(index);
      }
    }
    console.log(JSON.stringify({compatible,hashes,rule_indices:[...flagged]}));
  }catch{console.log(JSON.stringify({error:'Calibration bridge rejected input'}));}
}
