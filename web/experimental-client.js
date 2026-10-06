// No call site in app.js: ML remains off and canonical v1 review is unchanged.
export function reviewExperimental(envelopeJSON, artifactJSON, {signal, timeoutMs = 2000} = {}) {
  return new Promise((resolve,reject) => {
    if (![envelopeJSON,artifactJSON].every(text => typeof text === 'string' && text.length <= 2*1024*1024) || !Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 2000) { reject(new Error('Experimental request exceeds limits.')); return; }
    if (signal?.aborted) { reject(new Error('Experimental review cancelled.')); return; }
    const worker = new Worker(new URL('./experimental-worker.js', import.meta.url), {type:'module'});
    const finish = (error,value) => { clearTimeout(timer); signal?.removeEventListener('abort',abort); worker.terminate(); error ? reject(error) : resolve(value); };
    const abort = () => finish(new Error('Experimental review cancelled.'));
    const timer = setTimeout(() => finish(new Error('Experimental CPU time limit exceeded.')), timeoutMs);
    signal?.addEventListener('abort',abort,{once:true});
    worker.onmessage = ({data}) => finish(data.error ? new Error(data.error) : null,data);
    worker.onerror = () => finish(new Error('Experimental worker failed.'));
    worker.postMessage({envelopeJSON,artifactJSON});
  });
}
