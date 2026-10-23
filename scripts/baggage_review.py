"""Installed baggage wire grammar using the shared three-route recovery harness."""
import json
from pathlib import Path
import sys
from modern_validation_review import run_frames
from traceparent_review import frames, check, http_review

INVALID = [None, {}, True, '', ' ', '=x', 'bare', 'a=x,', ',a=x', 'a="x"', 'a=x\\y',
           'a=x y', 'a=é', 'a=%', 'a=%0', 'a=%xx', 'a=x;', 'a=x;=y', 'a=x;bad key',
           'a=x;property=%GG', 'a@b=x', 'a=x\ny', 'a=' + 'x' * 8191,
           ','.join('a=x' for _ in range(65))]
VALID = ['a=', 'A=x,a=y', ' a = %C3%A9%00%ff%25 ; bare ; property = =x ',
         'a=' + 'x' * 8190, ','.join('a=x' for _ in range(64))]


if __name__ == '__main__':
    executable = str(Path(sys.argv[1]).absolute())
    for modern in (False, True):
        check(run_frames(executable, frames(modern, 'baggage', INVALID, VALID)), 'baggage', INVALID, len(VALID))
    http_review(executable, 'baggage', INVALID, VALID)
    print(json.dumps({'status': 'PASS', 'routes': 3, 'invalid_rejections': len(INVALID) * 3,
                      'budget_recoveries': 3, 'valid_contexts': len(VALID) * 3, 'pings': 3}))
