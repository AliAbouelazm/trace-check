// Bounded worker calls. User data stays in this tab and its disposable worker.
function request(payload, {signal, timeoutMs = 2000, loadTimeoutMs = 15000, onProgress} = {}) {
  return new Promise((resolve,reject) => {
    const texts=payload.bundled ? [payload.envelopeJSON] : [payload.envelopeJSON,payload.artifactJSON];
    if (!texts.every(text => typeof text === 'string' && text.length <= 2*1024*1024) || !Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 2000 || !Number.isInteger(loadTimeoutMs) || loadTimeoutMs < 1 || loadTimeoutMs > 15000) { reject(new Error('Experimental request exceeds limits.')); return; }
    if (signal?.aborted) { reject(new Error('Experimental review cancelled.')); return; }
    const worker = new Worker(new URL('./experimental-worker.js', import.meta.url), {type:'module'});
    let settled=false;
    const finish = (error,value) => { if(settled)return;settled=true;clearTimeout(timer); signal?.removeEventListener('abort',abort); worker.terminate(); error ? reject(error) : resolve(value); };
    const abort = () => finish(new Error('Experimental review cancelled.'));
    let timer = setTimeout(() => finish(new Error(payload.bundled ? 'Local model load/verification time limit exceeded. Rules remain available.' : 'Experimental CPU time limit exceeded.')), payload.bundled ? loadTimeoutMs : timeoutMs);
    signal?.addEventListener('abort',abort,{once:true});
    worker.onmessage = ({data}) => {
      if(data.type==='ready'){if(payload.bundled){clearTimeout(timer);timer=setTimeout(()=>finish(new Error('Experimental CPU time limit exceeded.')),timeoutMs);}onProgress?.({stage:'Verified model. Scoring locally…'});return;}
      if(data.type==='progress'){onProgress?.(data);return;}
      finish(data.error ? new Error(data.error) : null,data);
    };
    worker.onerror = () => finish(new Error('Experimental worker failed. Rules remain available.'));
    worker.postMessage(payload);
  });
}
export function reviewExperimental(envelopeJSON, artifactJSON, options) {return request({envelopeJSON,artifactJSON},options);}
export function reviewBundled(envelopeJSON,options) {return request({envelopeJSON,bundled:true},options);}
