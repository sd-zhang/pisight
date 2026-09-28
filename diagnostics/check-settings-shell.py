#!/usr/bin/env python3
"""Check the settings script with the matching BusyBox hush executable.

Usage: check-settings-shell.py /path/to/busybox /path/to/isight-config-store
Only syntax, fail-fast behavior and invalid inputs are exercised; no mount or
settings writes occur. The original `set -eu` fails these validation checks.
"""
from pathlib import Path
import subprocess
import sys

busybox, script = sys.argv[1:]
subprocess.run([busybox, 'sh', '-n', script], check=True)
for args in [[], ['75', '0', 'activity', '2'], ['24', '0', 'activity', '1'],
             ['75', '21', 'activity', '1']]:
    p = subprocess.run([busybox, 'sh', script, '--locked', *args], capture_output=True, text=True)
    assert p.returncode == 2 and 'invalid option' not in p.stderr, (args, p.returncode, p.stderr)
flags = next(line for line in Path(script).read_text().splitlines() if line.startswith('set -'))
p = subprocess.run([busybox, 'sh', '-c', flags + '; false; echo UNREACHED'],
                   capture_output=True, text=True)
assert p.returncode == 1 and not p.stdout and not p.stderr, p
print('PASS: hush syntax, four invalid-input cases, and fail-fast behavior')
