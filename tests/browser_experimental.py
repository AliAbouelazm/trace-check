"""Synthetic browser parity and bounded-worker preflight. No fits or datasets."""
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experimental'))
from contract import artifact, encode
from fixtures import fixtures

root=Path(__file__).resolve().parents[1]
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
server=subprocess.Popen([sys.executable,str(root/'server.py'),'--port',str(port)],stdout=subprocess.DEVNULL)
stop=threading.Event();samples=[]
def sample_memory():
    # Linux process-tree RSS sum includes shared pages more than once, the test
    # driver and local server. It is NOT worker JS heap or an OS memory limit.
    while not stop.is_set():
        records={}
        for path in Path('/proc').glob('[0-9]*/status'):
            try:
                values=dict(line.split(':',1) for line in path.read_text().splitlines() if ':' in line)
                records[int(path.parent.name)]=(int(values['PPid']),int(values.get('VmRSS','0 kB').split()[0]))
            except (OSError,ValueError,KeyError):pass
        descendants={os.getpid()}
        while True:
            expanded=descendants|{pid for pid,(parent,_) in records.items() if parent in descendants}
            if expanded==descendants:break
            descendants=expanded
        samples.append(sum(records.get(pid,(0,0))[1] for pid in descendants))
        stop.wait(.05)
thread=threading.Thread(target=sample_memory,daemon=True);thread.start()
try:
    url=f'http://127.0.0.1:{port}'
    for _ in range(50):
        try:urllib.request.urlopen(url,timeout=1).close();break
        except OSError:time.sleep(.1)
    data=fixtures()
    # Caps were fixed before measurement: 20k features, 2 MiB each serialized
    # input/model, 2000 groups/steps, 12000 code points/feature, 2s worker timeout.
    vocabulary=[f'term{i:05d}' for i in range(10000)]+[f'term{i:05d} term{(i+1)%10000:05d}' for i in range(10000)]
    large_model=artifact(vocabulary,[1.23456789]*20000,[[round(math.sin(i+k),10) for i in range(20000)] for k in range(3)],[.1,.2,.3])
    terms=' '.join(vocabulary[:100])
    def envelope(count,content):
        steps=[{'id':str(i),'kind':'assistant','content':content} for i in range(count)]
        return {'envelope_version':1,'run':{'schema_version':1,'run_id':'synthetic-load','task':'Synthetic preflight','status':'completed','steps':steps},'messages':[{'role':'assistant','step_ids':[str(i)]} for i in range(count)]}
    loads=[('representative',data['envelopes'][0]),('max-groups',envelope(2000,terms[:800])),('max-fields',envelope(20,'a.'*49999+'@'))]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium'))
        page=browser.new_page();errors=[];requests=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:requests.append((request.method,request.url)))
        page.goto(url)
        assert not any('/experimental' in address for _,address in requests)
        time.sleep(.1)
        baseline_rss=samples[-1]
        parity=page.evaluate('''async data => {
          const {parseEnvelope,parseArtifact,feature,score}=await import('./experimental.js');
          const envs=data.envelopes.map(e=>parseEnvelope(JSON.stringify(e)));
          const model=parseArtifact(JSON.stringify(data.model));
          return {features:data.feature_cases.map(c=>feature(envs[c.envelope],c.index)),scores:data.score_cases.map(c=>score(model,c.text)),boundary:score(parseArtifact(JSON.stringify(data.boundary_model)),'aa')};
        }''',data)
        for expected,actual in zip(data['feature_cases'],parity['features']):assert expected['expected']==actual
        max_error=0
        for case,actual in zip(data['score_cases']+[{'expected':data['boundary_expected']}],parity['scores']+[parity['boundary']]):
            expected=case['expected'];assert expected['abstention']==actual['abstention'];assert expected['suggestion']==actual['suggestion']
            if expected['scores'] is None:assert actual['scores'] is None
            else:
                error=max(abs(x-y) for x,y in zip(expected['scores'],actual['scores']));max_error=max(max_error,error);assert error<=1e-6
        mapped=page.evaluate('''async data => {
          const {reviewExperimental}=await import('./experimental-client.js');
          return await reviewExperimental(JSON.stringify(data.envelopes[0]),JSON.stringify(data.model));
        }''',data)
        assert [(r['message_index'],r['step_index']) for r in mapped['results']]==[(1,1),(4,5)]
        assert all('step_id' not in r for r in mapped['results'])
        metrics={'feature_cases':len(parity['features']),'score_cases':len(parity['scores'])+1,'max_score_absolute_error':max_error,'model_bytes':len(encode(large_model).encode()),'loads':[]}
        for name,value in loads:
            payload={'envelopeJSON':encode(value),'artifactJSON':encode(large_model)}
            result=page.evaluate('''async payload => {
              const {reviewExperimental}=await import('./experimental-client.js');
              let ticks=0;const timer=setInterval(()=>ticks++,10);const start=performance.now();
              try {const result=await reviewExperimental(payload.envelopeJSON,payload.artifactJSON);return {wall_ms:performance.now()-start,worker_ms:result.elapsed_ms,ticks,count:result.results.length};}
              finally {clearInterval(timer);}
            }''',payload)
            expected_count=2 if name=='representative' else len(value['messages'])-1
            assert result['count']==expected_count
            assert result['wall_ms']<2000
            if name=='max-groups':assert result['ticks']>0
            metrics['loads'].append({'name':name,'input_bytes':len(payload['envelopeJSON'].encode()),**result})
        controls=page.evaluate('''async payload => {
          const {reviewExperimental}=await import('./experimental-client.js');
          const results=[];
          const controller=new AbortController();
          const work=reviewExperimental(payload.envelopeJSON,payload.artifactJSON,{signal:controller.signal});controller.abort();
          try{await work;results.push('FAILED');}catch(e){results.push(e.message);}
          try{await reviewExperimental(payload.envelopeJSON,payload.artifactJSON,{timeoutMs:1});results.push('FAILED');}catch(e){results.push(e.message);}
          try{await reviewExperimental('{}',payload.artifactJSON);results.push('FAILED');}catch(e){results.push(e.message);}
          return results;
        }''',payload)
        assert 'cancelled' in controls[0] and 'time limit' in controls[1] and 'Invalid' in controls[2],controls
        assert page.evaluate('localStorage.length === 0 && sessionStorage.length === 0')
        assert page.locator('#review').is_hidden()
        assert all(method=='GET' and address.startswith(url+'/') for method,address in requests)
        assert not errors,errors
        browser.close()
    metrics['baseline_harness_tree_rss_kib']=baseline_rss
    metrics['peak_harness_tree_rss_kib']=max(samples)
    metrics['sampled_rss_growth_kib']=max(samples)-baseline_rss
    print(json.dumps(metrics,indent=2))
finally:
    stop.set();thread.join(timeout=2)
    server.terminate();server.wait(timeout=5)
