import {parseEnvelope, parseArtifact, feature, score} from './experimental.js';
import {REVIEW_MODEL} from './review-model-info.js';
function truncation(envelope,index){
  const groups=envelope.groups.slice(Math.max(0,index-2),index+1);let perField=0,joined=0;
  for(const group of groups){
    if(group.role==='excluded')continue;
    const [main,...calls]=group.steps;
    const content=main.content.replace(/<an[sſ]wer>.*?<\/an[sſ]wer>/gis,'[answer omitted]');
    perField+=Math.max(0,Array.from(content).length-4000);
    joined+=group.role.length+1+Math.min(Array.from(content).length,4000)+1;
    for(const call of calls){const length=Array.from(call.content).length;perField+=Math.max(0,length-4000);joined+=Array.from(call.tool).length+1+Math.min(length,4000)+1;}
  }
  return {field_characters_removed:perField,joined_characters_removed:Math.max(0,joined-1-12000)};
}
self.onmessage = async event => {
  try {
    const {envelopeJSON,bundled} = event.data;
    const started = performance.now();
    self.postMessage({type:'progress',stage:'Checking original message groups'});
    const envelope = parseEnvelope(envelopeJSON);
    let artifactJSON=event.data.artifactJSON;
    if(bundled){
      self.postMessage({type:'progress',stage:'Loading and verifying local JSON model'});
      // Static data-string module uses script-src 'self'. connect-src stays 'none':
      // no fetch/upload endpoint or user-log network request is introduced.
      const data=await import('./review-model-data.js');
      artifactJSON=data.default;
      const bytes=new TextEncoder().encode(artifactJSON);
      if(bytes.length!==REVIEW_MODEL.bytes)throw new Error();
      const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
      if(digest!==REVIEW_MODEL.sha256)throw new Error();
    }
    const model = parseArtifact(artifactJSON);
    if(bundled && model.threshold!==REVIEW_MODEL.cutoff)throw new Error();
    const last = envelope.groups.findLastIndex(group => group.role === 'assistant');
    const positions = new Map(envelope.run.steps.map((step,index) => [step.id,index]));
    const indices=envelope.groups.map((g,i)=>g.role==='assistant'&&i<last?i:null).filter(i=>i!==null);
    const results = [];
    for (const index of indices){
      results.push({message_index:index,step_index:positions.get(envelope.groups[index].steps[0].id),truncation:truncation(envelope,index),...score(model,feature(envelope,index))});
      if(results.length%50===0)self.postMessage({type:'progress',stage:`Scoring ${results.length} of ${indices.length} actions`});
    }
    const unsupported=results.filter(r=>r.scores===null);
    const coverage={eligible_actions:results.length,scored_actions:results.length-unsupported.length,unsupported_actions:unsupported.length,final_assistant_excluded:last>=0?1:0,
      truncated_actions:results.filter(r=>r.truncation.field_characters_removed||r.truncation.joined_characters_removed).length,
      unsupported_reasons:Object.fromEntries([...new Set(unsupported.map(r=>r.abstention))].map(reason=>[reason,unsupported.filter(r=>r.abstention===reason).length]))};
    self.postMessage({results,coverage,elapsed_ms:performance.now()-started,model:bundled?REVIEW_MODEL:null,method:'Experimental uncalibrated review suggestions; not observed evidence.'});
  } catch {
    self.postMessage({error:'Review input or local model failed its bounded integrity checks. Rules remain available.'});
  }
};
