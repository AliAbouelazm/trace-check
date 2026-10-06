import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

SERVER=Path(__file__).resolve().parents[1]/'server.py'

class StartupTests(unittest.TestCase):
    def test_one_command_from_other_directory_and_available_port(self):
        with tempfile.TemporaryDirectory() as cwd:
            process=subprocess.Popen([sys.executable,str(SERVER),'--port','0'],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                line=process.stdout.readline().strip()
                self.assertTrue(line.startswith('Trace Check: http://127.0.0.1:'))
                url=line.removeprefix('Trace Check: ')
                with urllib.request.urlopen(url,timeout=3) as response:
                    self.assertEqual(response.status,200)
                    self.assertIn(b'Choose JSON file',response.read())
                self.assertNotEqual(url.rsplit(':',1)[1],'0')
            finally:
                process.terminate();process.communicate(timeout=3)
    def test_occupied_and_invalid_ports_explain_recovery(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));sock.listen()
            result=subprocess.run([sys.executable,str(SERVER),'--port',str(sock.getsockname()[1])],capture_output=True,text=True,timeout=3)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('--port 0',result.stderr)
        self.assertNotIn('http://',result.stdout)
        self.assertNotIn('Traceback',result.stderr)
        result=subprocess.run([sys.executable,str(SERVER),'--port','65536'],capture_output=True,text=True,timeout=3)
        self.assertNotEqual(result.returncode,0);self.assertIn('0 to 65535',result.stderr)
