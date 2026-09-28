from pathlib import Path
import subprocess,sys,tempfile
script=Path(sys.argv[1]).read_text();start=script.index('\t\t# Selectors 1:')
end=script.index('\n\t\tcd $OLDPWD',start)
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'bNumControls').write_text('0\n')
    subprocess.run(['/bin/sh','-ec',script[start:end]],cwd=tmp,check=True)
    assert (p/'guidExtensionCode').read_bytes()==b'PiSightSettings1'
    bitmap=int((p/'bmControls').read_text(),0);count=int((p/'bNumControls').read_text())
    assert bitmap==3 and count==2, f'FAIL: bitmap={bitmap} bNumControls={count}, expected two advertised controls'
    print('PASS: gadget setup advertises both XU controls with unchanged GUID')
