"""Linux pre-fit supervisor. Never invoked by the app or ordinary model tests."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def run_bounded(command, *, seconds=60, rss_mib=512):
    if not 0 < seconds <= 60 or not 0 < rss_mib <= 512:
        raise ValueError('Cannot increase reviewed CPU process budgets')
    if not Path('/proc/self/status').exists():
        raise RuntimeError('RSS supervisor requires Linux /proc')
    environment={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    started=time.monotonic()
    child=subprocess.Popen(command,env=environment,start_new_session=True)
    peak=0;reason=None
    def stop_group():
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    try:
        while child.poll() is None:
            rss=0
            for path in Path('/proc').glob('[0-9]*/status'):
                try:
                    if os.getpgid(int(path.parent.name)) != child.pid:continue
                    for line in path.read_text().splitlines():
                        if line.startswith('VmRSS:'):rss+=int(line.split()[1])
                except (OSError,ValueError):pass
            peak=max(peak,rss)
            if time.monotonic()-started >= seconds:reason='wall-time'
            elif rss > rss_mib*1024:reason='rss'
            if reason:
                stop_group();break
            time.sleep(.01)
        code=child.wait()
    finally:
        # No surviving helper processes on success, failure or interruption.
        stop_group()
        child.wait()
    result={'exit_code':code,'stop_reason':reason,'elapsed_seconds':time.monotonic()-started,'sampled_peak_group_rss_kib':peak,'rss_poll_seconds':.01}
    return result

if __name__ == '__main__':
    command=sys.argv[1:]
    if command[:1]==['--']:command=command[1:]
    if not command:raise SystemExit('Provide a reviewed command after --')
    result=run_bounded(command)
    print(json.dumps(result),flush=True)
    raise SystemExit(1 if result['stop_reason'] or result['exit_code'] else 0)
