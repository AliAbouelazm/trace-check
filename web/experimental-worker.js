import {parseEnvelope, parseArtifact, feature, score} from './experimental.js';
self.onmessage = event => {
  try {
    const {envelopeJSON, artifactJSON} = event.data;
    const started = performance.now();
    const envelope = parseEnvelope(envelopeJSON), model = parseArtifact(artifactJSON);
    const last = envelope.groups.findLastIndex(group => group.role === 'assistant');
    const positions = new Map(envelope.run.steps.map((step,index) => [step.id,index]));
    const results = [];
    for (let index = 0; index < last; index++) if (envelope.groups[index].role === 'assistant') results.push({message_index:index,step_index:positions.get(envelope.groups[index].steps[0].id),...score(model,feature(envelope,index))});
    self.postMessage({results, elapsed_ms:performance.now()-started, method:'Experimental uncalibrated model suggestions; not observed evidence.'});
  } catch {
    // Do not echo any user-supplied text or model fields in errors.
    self.postMessage({error:'Invalid or unsupported experimental input.'});
  }
};
