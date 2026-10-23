"""Installed tracestate grammar checks with shared three-route recovery harness."""
import json
from pathlib import Path
import sys
from modern_validation_review import run_frames
from traceparent_review import frames, check, http_review

INVALID = [None, {}, True, 'a=', '=x', 'A=x', '1=x', 'a=x,a=y', 'a=x=y', 'a=x\ny',
           'a=x\ty', 'a=é', 'a.b=x', 'a @b=x', 'a@1=x', '@a=x', 'a@@b=x',
           'a' * 257 + '=x', 'a=' + 'x' * 257, 'a' * 242 + '@b=x', 'a@' + 'b' * 15 + '=x',
           ','.join('a'+str(i)+'=x' for i in range(33)), ' ' * 32769]
VALID = ['', ' \ta= x \t,1@system=Y', ','.join('a'+str(i)+'=x' for i in range(32)), 'a' * 256 + '=' + 'x' * 256, ' ' * 32768]


if __name__ == '__main__':
    executable = str(Path(sys.argv[1]).absolute())
    for modern in (False, True):
        check(run_frames(executable, frames(modern, 'tracestate', INVALID, VALID)), 'tracestate', INVALID, len(VALID))
    http_review(executable, 'tracestate', INVALID, VALID)
    print(json.dumps({'status': 'PASS', 'routes': 3, 'invalid_rejections': len(INVALID) * 3,
                      'budget_recoveries': 3, 'valid_contexts': len(VALID) * 3, 'pings': 3}))
