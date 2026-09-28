from pathlib import Path
import os
import subprocess,tempfile,sys
source=(Path(os.environ.get('WEBCAMPI_ROOT','webcampi'))/'board/raspberrypizero/rootfs-overlay/etc/init.d/S62pisight-diagnostic').read_text()
body=source[source.index('microphone_log()'):source.index('\n# Snapshot readback')]
with tempfile.TemporaryDirectory() as d:
 p=Path(d); (p/'mic').write_text(''.join(f'original line {i}\n' for i in range(300)))
 script=p/'probe.sh'
 script.write_text('MIC_LOG="$1/mic"\nMIC_LOG_BYTES=0\n'+body+'''\nmicrophone_log > "$1/first"
microphone_log > "$1/empty"
printf 'new sample\\n' >> "$MIC_LOG"
microphone_log > "$1/second"
printf 'rotated sample\\n' > "$MIC_LOG"
microphone_log > "$1/rotated"
''')
 subprocess.run(sys.argv[1:]+[str(script),str(p)],check=True)
 assert (p/'first').read_text()==''.join(f'original line {i}\n' for i in range(300))
 assert not (p/'empty').read_text()
 assert (p/'second').read_text()=='new sample\n'
 assert (p/'rotated').read_text()=='rotated sample\n'
 print('PASS: complete microphone log, incremental reads, truncation recovery')
