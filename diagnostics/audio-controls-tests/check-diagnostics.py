"""Run actual snapshot gating/rotation with only hardware collection replaced."""
from pathlib import Path
import os
import subprocess, sys, tempfile
source=(Path(os.environ.get('WEBCAMPI_ROOT','webcampi'))/'board/raspberrypizero/rootfs-overlay/etc/init.d/S62pisight-diagnostic').read_text()
assert 'copy_to_card' not in source and 'remount' not in source and 'sync' not in source
body=source[:source.index('\ncase "$1" in')]
start=body.index('\n\t{',body.index('snapshot()'))
end=body.index(' > "$LOG.next"',start)
body=body[:start]+ '\n\t{ head -c 300000 /dev/zero; [ ! -f "$TEST_ROOT/disable-during" ] || echo 0 > "$TEST_ROOT/flag"; }' +body[end:]
body=body.replace('LOG=/tmp/PISIGHT.TXT','LOG="$TEST_ROOT/log"').replace('/run/pisight-diagnostics','"$TEST_ROOT/flag"')
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);script=p/'test.sh'
 script.write_text('TEST_ROOT="$1"\n'+body+'''
snapshot off
[ ! -e "$LOG" ] || exit 1
echo 1 > "$TEST_ROOT/flag"
snapshot on
[ "$(wc -c < "$LOG")" -eq 262144 ] || exit 2
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do snapshot on; done
[ "$(wc -c < "$LOG")" -eq 4194304 ] || exit 3
snapshot rotated
[ "$(wc -c < "$LOG")" -eq 262144 ] || exit 4
echo 0 > "$TEST_ROOT/flag"
snapshot off
[ "$(wc -c < "$LOG")" -eq 262144 ] || exit 5
echo 1 > "$TEST_ROOT/flag"
touch "$TEST_ROOT/disable-during"
snapshot cancelled
[ "$(wc -c < "$LOG")" -eq 262144 ] && [ ! -e "$LOG.next" ] || exit 6
''')
 subprocess.run(sys.argv[1:]+[str(script),str(p)],check=True)
 print('PASS: missing/off flag suppresses collection, live enable/disable, 4 MiB rotation, mid-collection cancellation; no SD write path')
