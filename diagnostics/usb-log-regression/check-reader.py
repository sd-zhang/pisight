from pathlib import Path
import importlib.util,subprocess,sys,tempfile
module=Path('diagnostics/read-usb-diagnostics.py')
assert module.exists(), 'FAIL: host diagnostic reader missing'
spec=importlib.util.spec_from_file_location('reader',module);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);fixture=root/'log';data=bytes(range(256))*997+bytes(range(19));fixture.write_bytes(data)
    counters=root/'counters';counters.write_bytes(b'ep1in disabled missed=4\n')
    exe=root/'server'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(Path(sys.argv[1])/'lib'),'diagnostics/usb-log-regression/server.c','-o',str(exe)],check=True)
    proc=subprocess.Popen([str(exe),str(fixture),str(counters)],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    cached=b''
    def exchange(direction,request,payload):
        global cached
        if direction=='out':
            proc.stdin.write(payload);proc.stdin.flush();cached=proc.stdout.read(60);return len(payload)
        if request==0x85:return b'\x3c\0'
        return cached
    try:
        assert reader.fetch_snapshot(exchange,0)==data
        assert reader.fetch_snapshot(exchange,1)==counters.read_bytes()
        for mode in ['short','generation','offset','total','length','padding']:
            def broken(direction,request,payload):
                reply=exchange(direction,request,payload)
                if direction=='in' and request==0x81:
                    r=bytearray(reply)
                    if mode=='short':return bytes(r[:-1])
                    if mode=='generation' and int.from_bytes(r[12:16],'little'):r[4]^=1
                    if mode=='offset':r[12]^=1
                    if mode=='total' and int.from_bytes(r[12:16],'little'):r[8]^=1
                    if mode=='length':r[2]=45
                    if mode=='padding' and r[2]<44:r[-1]=1
                    return bytes(r)
                return reply
            try:reader.fetch_snapshot(broken,1 if mode=='padding' else 0)
            except (ValueError,RuntimeError):pass
            else:raise AssertionError('accepted damaged '+mode+' response')
        print('PASS: actual C snapshot -> host reader preserves 255251 binary bytes; rejects short/mixed/wrong-offset/size/length/padding responses')
    finally:proc.stdin.close();proc.wait(timeout=5);assert proc.returncode==0
