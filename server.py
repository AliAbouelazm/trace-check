"""Local static server. No upload endpoint, storage, or request logging."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / 'web'), **kwargs)
    def log_message(self, *args): pass
    def end_headers(self):
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        super().end_headers()
    def list_directory(self, path):
        self.send_error(404)

def port_number(value):
    number = int(value)
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError('Port must be from 0 to 65535.')
    return number

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start Trace Check on this computer. No account or package install is required.')
    parser.add_argument('--port', type=port_number, default=8765, help='local port (default: 8765); 0 selects an available port')
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError:
        parser.error(f'Could not open local port {args.port}. Try --port 0 to select an available port.')
    with server:
        print(f'Trace Check: http://127.0.0.1:{server.server_port}', flush=True)
        print('Open this address in your browser. Press Ctrl+C to stop.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
