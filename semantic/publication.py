"""Final offline publication gate, including between-poll completion overruns."""
import json
from pathlib import Path

WALL_SECONDS = 120
RSS_KIB = 2048 * 1024


def within_limit(value, ceiling):
    return type(value) in (int, float) and 0 <= value <= ceiling


def publish_preflight(result_path, output_path, supervision):
    # A worker can exit after the last polling check. Its final supervisor
    # accounting must independently pass before even reading the staged report.
    if not (
        type(supervision.get('exit_code')) is int
        and supervision['exit_code'] == 0
        and 'stop_reason' in supervision
        and supervision['stop_reason'] is None
        and within_limit(supervision.get('elapsed_seconds'), WALL_SECONDS)
        and within_limit(supervision.get('sampled_peak_group_rss_kib'), RSS_KIB)
    ):
        raise ValueError('Final preflight resource accounting failed')
    result = json.loads(Path(result_path).read_text())
    if result.get('status') != 'synthetic-preflight-only':
        raise ValueError('Successful synthetic preflight report required')
    result['supervision'] = supervision
    result['limits'] = {'wall_seconds': WALL_SECONDS, 'sampled_process_group_rss_mib': RSS_KIB // 1024}
    serialized = json.dumps(result, indent=2, allow_nan=False)
    with Path(output_path).open('x') as output:
        output.write(serialized)
    return result
