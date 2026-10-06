"""Package allowlisted static assets for PRIVATE publication review, never deploy.

Default: incomplete model-free review archive. --complete: audited static release
candidate with the unchanged frozen model. Neither mode authorizes deployment.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSETS=('index.html','app.js','styles.css','core.js','examples.js','experimental.js','experimental-client.js','experimental-worker.js','review-demo.js','illustrative-suggestion.js','review-model-info.js','review-model-NOTICE.txt','example-NOTICE.txt','THIRD-PARTY-NOTICES.txt')
BLOCKER='PRIVATE PUBLICATION REVIEW ONLY. Model data module omitted: privacy/license clearance pending. Rules work; ML controls and handler are disabled before any worker/model request. Do not publish this archive as a complete ML app. No deployment authorized. Configure HTTPS and enforce response security headers; _headers syntax is host-specific and must be verified on the actual host. No raw dataset or research files are included.\n'
def review_asset(name, data):
    """Explicit review-only UI; no worker/model request can start from controls."""
    if name == 'index.html':
        marker='<section class="intro">'
        replacement='<aside role="alert" class="panel"><strong>INCOMPLETE PRIVATE REVIEW BUNDLE</strong><p>Experimental ML is disabled because its model is excluded pending privacy and license review. Only structural rules are available. This is not a cleared public release.</p></aside>'+marker
        text=data.decode();assert text.count(marker)==1
        return text.replace(marker,replacement).encode()
    if name == 'app.js':
        text=data.decode()
        replacements={
            "$('ml-enable').disabled = !originalEnvelope;":"$('ml-enable').disabled = true;",
            "$('ml-status').textContent = originalEnvelope ? 'Off for this run. Original message grouping is available.' : 'Unavailable: this run lacks explicit original message grouping. Rules remain available.';":"$('ml-status').textContent = 'Unavailable in this incomplete review bundle: model excluded pending publication audit. Rules remain available.';",
            "$('ml-enable').addEventListener('change', async () => {":"$('ml-enable').addEventListener('change', async () => { resetML(); $('ml-status').textContent='ML disabled in this incomplete review bundle.'; return;"
        }
        for old,new in replacements.items():
            if text.count(old)!=1:raise ValueError('Review-only guard source changed; abort bundle')
            text=text.replace(old,new)
        return text.encode()
    return data

def package(output, complete=False):
    inventory=[]
    assets=ASSETS+('review-model-data.js',) if complete else ASSETS
    model_sha='10bf769e803e38cd50aef8af86599b482e9e585fc8e59c95a711d517774ec164'
    if complete:
        module=(ROOT/'web/review-model-data.js').read_text()
        payload=json.loads(module.split('export default ',1)[1].strip().removesuffix(';')).encode()
        if len(payload)!=1866714 or hashlib.sha256(payload).hexdigest()!=model_sha:raise ValueError('Frozen model changed; release aborted')
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in assets:
            data=(ROOT/'web'/name).read_bytes()
            if not complete:data=review_asset(name,data)
            archive.writestr(name,data)
            inventory.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        archive.writestr('_headers',(ROOT/'deployment/_headers').read_bytes())
        archive.writestr('RELEASE-REVIEW.txt' if complete else 'PUBLICATION-BLOCKED.txt', 'Complete static candidate; not deployed and deployment is not authorized. Includes the unchanged source-derived model and third-party notices. Serve only after user approval over HTTPS with enforced response CSP/frame/no-referrer headers; verify no analytics and cold loading on the chosen host. Residual provenance/rights limitations are in THIRD-PARTY-NOTICES.txt.\n' if complete else BLOCKER)
        archive.writestr('asset-manifest.json',json.dumps({'publication_approved':False,'model_included':complete,'model_payload_sha256':model_sha if complete else None,'assets':inventory},indent=2))
    return {'archive':str(output),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'publication_approved':False,'model_included':complete,'asset_count':len(inventory)}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--complete',action='store_true',help='Include the audited unchanged model; never deploy');args=parser.parse_args();print(json.dumps(package(args.output,args.complete)))
