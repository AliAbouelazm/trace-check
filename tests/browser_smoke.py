"""Starts the local app server, or uses TRACE_CHECK_URL when supplied."""
import json
import os
import shutil
import atexit
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url = os.environ.get('TRACE_CHECK_URL')
if not url:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    server = subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1] / 'server.py'), '--port', str(port)], stdout=subprocess.DEVNULL)
    def stop_server():
        server.terminate(); server.wait(timeout=5)
    atexit.register(stop_server)
    url = f'http://127.0.0.1:{port}'
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1).close(); break
        except OSError: time.sleep(.1)
    else: raise RuntimeError('Local server did not start')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=os.environ.get("CHROMIUM_PATH") or shutil.which("chromium"))
    page = browser.new_page(viewport={'width': 1280, 'height': 1000})
    errors = []
    requests = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append((request.method, request.url)))
    response = page.goto(url)
    assert response.headers['cache-control'] == 'no-store'
    assert "connect-src 'none'" in response.headers['content-security-policy']
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    with page.expect_download() as event:
        page.get_by_role('button', name='Download sample', exact=True).click()
    sample_bytes = Path(event.value.path()).read_bytes()
    page.locator('#file').set_input_files({'name':'sample.json','mimeType':'application/json','buffer':sample_bytes})
    expect(page.locator('#review')).to_be_visible()
    page.get_by_role('button', name='Explore and recover', exact=True).click()
    assert page.locator('.step').count() == 9
    assert page.locator('.flag').count() == 1
    page.locator('#flagged').check()
    assert page.locator('.step').count() == 1
    page.locator('#flagged').uncheck()
    page.locator('#search').fill('Node.js')
    assert page.locator('.step').count() == 1
    page.locator('#search').fill('')
    page.locator('#kind').select_option('tool_call')
    assert page.locator('.step').count() == 3
    page.get_by_role('button', name='Repeated calls and missing evidence', exact=True).click()
    assert page.locator('.flag').count() == 3
    run = {'schema_version':1,'run_id':'unsafe','task':'Contact demo@example.com password=supersecret','status':'completed','steps':[{'id':'1','kind':'assistant','content':'<img src=x onerror="window.PWNED=1"> <script>window.PWNED=1</script>'}]}
    page.locator('#file').set_input_files({'name':'safe.json','mimeType':'application/json','buffer':json.dumps(run).encode()})
    expect(page.locator('#run-title')).to_have_text('unsafe')
    assert page.evaluate('window.PWNED') is None
    assert page.locator('#timeline img').count() == 0
    assert 'supersecret' not in page.locator('#task').inner_text()
    assert '[REDACTED EMAIL]' in page.locator('#task').inner_text()
    with page.expect_download() as event:
        page.get_by_role('button', name='Export report', exact=True).click()
    report = json.loads(Path(event.value.path()).read_text())
    assert report['redaction_count'] == 2
    assert 'supersecret' not in json.dumps(report)
    assert '_flags' not in report['run']['steps'][0]
    run['steps'] = [
        {'id':'one@example.com','kind':'tool_call','call_id':'key@example.com','content':'lookup'},
        {'id':'two@example.com','kind':'tool_result','call_id':'key@example.com','content':'failed password=never-export-me'}]
    page.locator('#file').set_input_files({'name':'links.json','mimeType':'application/json','buffer':json.dumps(run).encode()})
    expect(page.locator('.flag')).to_have_count(1)
    with page.expect_download() as event:
        page.locator('#export').click()
    report = json.loads(Path(event.value.path()).read_text())
    assert report['flags'][0]['step_id'] == report['run']['steps'][1]['id']
    assert report['run']['steps'][0]['call_id'] == report['run']['steps'][1]['call_id']
    assert 'never-export-me' not in json.dumps(report)
    assert '@example.com' not in json.dumps(report)
    quoted_cases = [
        '{"password":"correct horse battery staple"}',
        'api_key="abc;def,ghi"',
        r'password="first \"hidden quote\" trailing"',
        r"secret='first \'hidden quote\' trailing'",
        r'access_token="first \\ trailing"',
        'password="first\ntrailing"',
        'secret="first\nunterminated']
    for secret_text in quoted_cases:
        content = 'failed ' + secret_text
        run['task'] = content
        run['steps'] = [{'id':'1','kind':'tool_result','content':content}]
        page.locator('#file').set_input_files({'name':'quoted.json','mimeType':'application/json','buffer':json.dumps(run).encode()})
        expect(page.locator('.flag')).to_have_count(1)
        for selector in ['#task', '.content', '.flag']:
            shown = page.locator(selector).inner_text()
            assert '[REDACTED]' in shown, shown
            for forbidden in ['correct', 'horse', 'battery', 'staple', 'abc', 'def,ghi', 'first', 'hidden quote', 'trailing', 'unterminated']:
                assert forbidden not in shown, shown
        with page.expect_download() as event:
            page.locator('#export').click()
        serialized = Path(event.value.path()).read_text()
        for forbidden in ['correct', 'horse', 'battery', 'staple', 'abc', 'def,ghi', 'first', 'hidden quote', 'trailing', 'unterminated']:
            assert forbidden not in serialized, serialized
        assert 'Redaction is best effort' in serialized
    # Exercise the full import/render path near the file bound, including the
    # trailing-@ adversary, rather than timing only a presence shortcut.
    for suffix in ['', '@']:
        run['task'] = 'Large local review'
        run['steps'] = [{'id':str(i),'kind':'assistant','content':('a.' * 50000)[:100000 - len(suffix)] + suffix} for i in range(20)]
        payload = json.dumps(run).encode()
        assert len(payload) <= 2 * 1024 * 1024
        started = time.monotonic()
        page.locator('#file').set_input_files({'name':'large.json','mimeType':'application/json','buffer':payload})
        expect(page.locator('.step')).to_have_count(20)
        elapsed = time.monotonic() - started
        assert elapsed < 5, elapsed
        print(f'Browser ~2 MB import/render suffix={suffix!r}: {elapsed:.3f}s')
    assert page.evaluate('localStorage.length === 0 && sessionStorage.length === 0')
    page.reload()
    expect(page.locator('#review')).to_be_hidden()
    page.get_by_role('button', name='Explore and recover', exact=True).click()
    page.get_by_role('button', name='Clear run', exact=True).click()
    assert page.locator('#review').is_hidden()
    assert page.locator('#timeline').inner_text() == ''
    for buffer, message in [(b'{bad', 'not valid JSON'), (json.dumps({**run,'label':True}).encode(),'unknown field'), (json.dumps({**run,'schema_version':2}).encode(),'schema_version'), (json.dumps({**run,'steps':[run['steps'][0],run['steps'][0]]}).encode(),'duplicate'), (b' ' * (2*1024*1024+1), 'too large')]:
        page.locator('#file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':buffer})
        expect(page.locator('#error')).to_contain_text(message)
        assert page.locator('#review').is_hidden()
    page.get_by_role('button', name='Explore and recover', exact=True).click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert all(method == 'GET' and request_url.startswith(url + '/') for method, request_url in requests), requests
    assert page.request.post(url, data='untrusted log').status == 501
    assert page.request.get(url + '/.git/config').status == 404
    assert not errors, errors
    browser.close()
print('Browser smoke passed: examples, upload, filters, escaped content, redaction, export, clear, errors, mobile layout.')
