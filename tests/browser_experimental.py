"""Synthetic browser parity and bounded-worker preflight. No fits or datasets."""
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from browser_support import launch_chromium
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
        browser=launch_chromium(p)
        page=browser.new_page();errors=[];requests=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:requests.append((request.method,request.url)))
        page.goto(url)
        assert not any('/review-model-data.js' in address or '/experimental-worker.js' in address for _,address in requests)
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
        assert 'cancelled' in controls[0] and 'time limit' in controls[1] and 'integrity checks' in controls[2],controls
        # Actual reconstructed artifact: reference scores were captured once in
        # the authorized reconstruction, not generated by this browser scorer.
        golden=json.loads((root/'tests/fixtures/reconstructed-model-golden.json').read_text())
        actual=page.evaluate("""async golden => {
          const {parseArtifact,score}=await import('./experimental.js');
          const data=await import('./review-model-data.js');
          const model=parseArtifact(data.default);
          return golden.map(c=>score(model,c.text));
        }""",golden)
        actual_error=0
        for case,result in zip(golden,actual):
            expected=case['expected']
            assert result['suggestion']==expected['suggestion'] and result['abstention']==expected['abstention']
            if expected['scores'] is None:assert result['scores'] is None
            else:
                error=max(abs(a-b) for a,b in zip(expected['scores'],result['scores']))
                actual_error=max(actual_error,error);assert error<=1e-6
        metrics['actual_reconstructed_browser_golden_cases']=len(golden)
        metrics['actual_reconstructed_browser_max_error']=actual_error
        page.locator('#ml-demo').click()
        assert not page.locator('#ml-enable').is_checked()
        page.locator('#ml-enable').check()
        page.wait_for_function("() => !document.querySelector('#ml-export').disabled")
        assert '2/2 eligible actions scored' in page.locator('#ml-status').inner_text()
        assert page.locator('.ml-card').count()==2
        assert page.locator('#ml-cancel').is_hidden()
        page.locator('.ml-card button').first.click()
        assert page.evaluate("document.activeElement.id==='timeline-step-1'")
        with page.expect_download() as dl:page.locator('#ml-export').click()
        notes=json.loads(Path(dl.value.path()).read_text())
        assert notes['model']['sha256']=='10bf769e803e38cd50aef8af86599b482e9e585fc8e59c95a711d517774ec164'
        assert notes['model']['automatic_promotion_eligible'] is False
        assert notes['coverage']['scored_actions']==2 and 'messages' not in notes
        # Cancel at the user interaction boundary, before worker publication.
        page.evaluate("document.querySelector('#ml-enable').click();document.querySelector('#ml-enable').click();document.querySelector('#ml-cancel').click()")
        assert 'cancelled' in page.locator('#ml-status').inner_text()
        assert page.locator('#ml-export').is_disabled()
        # A new run resets opt-in and original grouping is never inferred.
        page.locator('#examples button').first.click()
        assert page.locator('#ml-enable').is_disabled() and not page.locator('#ml-enable').is_checked()
        assert 'lacks explicit original message grouping' in page.locator('#ml-status').inner_text()
        unicode_run=envelope(3,'café')
        page.locator('#file').set_input_files({'name':'unicode.json','mimeType':'application/json','buffer':json.dumps(unicode_run).encode()})
        page.locator('#ml-enable').check()
        page.wait_for_function("() => !document.querySelector('#ml-export').disabled")
        assert '2 unsupported' in page.locator('#ml-status').inner_text()
        assert 'unsupported-unicode' in page.locator('#ml-results').inner_text()
        # Real illustrative positive and explicit benign support boundary.
        page.locator('#ml-development').click();page.locator('#ml-enable').check()
        page.wait_for_function("() => !document.querySelector('#ml-export').disabled")
        assert page.locator('.ml-card.suggested').count()==1
        assert '0.7299' in page.locator('.ml-card.suggested').inner_text()
        assert 'index.html' in page.locator('.ml-card.suggested').inner_text()
        page.locator('.ml-card.suggested summary').click()
        window=page.locator('.ml-card.suggested details pre').inner_text()
        assert 'cd' in window and 'echo' in window and 'index.html' in window
        assert 'styles.css' not in window and 'No such file' not in window
        assert 'does not show that the model recognized' in page.locator('#example-evidence').inner_text()
        assert 'NOT an unseen benchmark' in page.locator('#example-evidence').inner_text()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#ml-unicode').click();page.locator('#ml-enable').check()
        page.wait_for_function("() => !document.querySelector('#ml-export').disabled")
        assert '1 unsupported' in page.locator('#ml-status').inner_text()
        page.set_viewport_size({'width':1280,'height':900})
        # Cold uncached local asset: transfer takes >2 seconds but remains within
        # the independent 15-second loading budget. No timeout increase for CPU.
        session=page.context.new_cdp_session(page)
        session.send('Network.enable');session.send('Network.setCacheDisabled',{'cacheDisabled':True})
        session.send('Network.emulateNetworkConditions',{'offline':False,'latency':20,'downloadThroughput':500000,'uploadThroughput':500000})
        page.locator('#ml-development').click();page.locator('#ml-enable').check()
        page.wait_for_function("() => !document.querySelector('#ml-export').disabled")
        assert page.locator('.ml-card.suggested').count()==1
        with page.expect_download() as cold:page.locator('#ml-export').click()
        cold_notes=json.loads(Path(cold.value.path()).read_text())
        assert cold_notes['elapsed_ms']>2000 and cold_notes['inference_ms']<2000
        metrics['cold_bundled_total_ms']=cold_notes['elapsed_ms'];metrics['cold_bundled_inference_ms']=cold_notes['inference_ms']
        # Cancel, clear and replacement during transfer cannot publish stale results.
        page.locator('#ml-development').click();page.locator('#ml-enable').check();page.locator('#ml-cancel').click()
        assert 'cancelled' in page.locator('#ml-status').inner_text() and page.locator('#ml-export').is_disabled()
        page.locator('#ml-development').click();page.locator('#ml-enable').check();page.locator('#clear').click()
        assert page.locator('#review').is_hidden()
        page.locator('#ml-development').click();page.locator('#ml-enable').check();page.locator('#ml-unicode').click()
        assert not page.locator('#ml-enable').is_checked() and page.locator('#ml-export').is_disabled()
        session.send('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1});session.detach()
        limit=page.evaluate("""async () => {const {reviewBundled}=await import('./experimental-client.js');const {demoEnvelope}=await import('./review-demo.js');try {await reviewBundled(JSON.stringify(demoEnvelope),{loadTimeoutMs:1});return 'FAILED';}catch(e){return e.message;}}""")
        assert 'load/verification time limit' in limit
        # Integrity failure is surfaced; neither rules nor the run disappear.
        page.locator('#clear').click()
        page.route('**/review-model-data.js',lambda route:route.fulfill(status=200,content_type='text/javascript',body='export default "{}";'))
        page.locator('#ml-demo').click();page.locator('#ml-enable').check()
        page.wait_for_function("() => document.querySelector('#ml-status').textContent.includes('integrity checks')")
        assert page.locator('#timeline .step').count()==8
        assert page.locator('#ml-export').is_disabled()
        page.unroute('**/review-model-data.js')
        page.locator('#clear').click()
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
