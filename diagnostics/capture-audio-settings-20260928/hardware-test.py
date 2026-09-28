import importlib.util, json, os, pathlib, struct, subprocess, time, hashlib
ROOT=pathlib.Path('/Users/steven/Documents/Git/pisight')
OUT=ROOT/'diagnostics/capture-audio-settings-20260928'
spec=importlib.util.spec_from_file_location('reader',ROOT/'diagnostics/read-usb-diagnostics.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
u=r.UsbReader(); records=[]; token=1000

def get(selector):
    p=u.transfer(0xa1,0x81,selector<<8,u.index,32)
    assert len(p)==32 and p[0]==1,p.hex()
    d={'time':time.time(),'selector':selector,'status':p[1],'flags':p[2],'token':struct.unpack_from('<I',p,4)[0],'hex':p.hex()}
    if selector==3:
        d.update(requested=list(struct.unpack_from('<hHHB',p,8)),applied=list(struct.unpack_from('<hHHB',p,16)),peak=struct.unpack_from('<H',p,24)[0],clips=struct.unpack_from('<I',p,28)[0])
    else:d.update(enabled=p[8],saved=p[16])
    records.append(d); (OUT/'uvc-settings.json').write_text(json.dumps(records,indent=2));return d

def apply(selector,value):
    global token
    token+=1;p=bytearray(32);p[0]=1;p[1]=1;struct.pack_into('<I',p,4,token)
    if selector==3:struct.pack_into('<hHHB',p,8,*value)
    else:p[8]=value
    assert u.transfer(0x21,1,selector<<8,u.index,bytes(p))==32
    d=get(selector);assert d['token']==token and d['status']==0,d
    assert (d['requested'] if selector==3 else d['enabled'])==value,d
    return d

def fetch(name,source=0):
    data=r.fetch_snapshot(u.exchange,source);(OUT/name).write_bytes(data);return data

original_audio=None;original_diag=None;child=None
try:
    for sel in [3,4]:
        assert u.transfer(0xa1,0x85,sel<<8,u.index,2)==b'\x20\x00'
        assert u.transfer(0xa1,0x86,sel<<8,u.index,1)==b'\x03'
    original_audio=get(3)['requested'];original_diag=get(4)['enabled']
    print('Initial settings:',original_audio,'diagnostics:',original_diag,flush=True)
    assert original_audio==[0,80,8000,0] and original_diag==0,'Unexpected initial settings; preserved'
    fetch('before-usb-counters.log',1)
    apply(4,1)
    env=dict(os.environ,PISIGHT_MIC_NAME='iSight Microphone')
    child=subprocess.Popen(['bash',str(ROOT/'diagnostics/run-concurrent-capture.sh'),str(OUT)],cwd=ROOT,env=env)
    started=time.monotonic(); next_meter=25
    while child.poll() is None:
        elapsed=time.monotonic()-started
        if elapsed>=next_meter and elapsed<145:
            d=get(3);print('Audio meter:',d['peak'],'clips:',d['clips'],'flags:',d['flags'],flush=True);next_meter+=40
        time.sleep(1)
    assert child.returncode==0,child.returncode
    child=None
    print('Baseline capture finished; checking live tuning during simultaneous capture.',flush=True)
    log=open(OUT/'post-readback-combined.log','w')
    child=subprocess.Popen([str(OUT/'capture-timing'),'90'],env=dict(env,PISIGHT_RESULT=str(OUT/'post-readback-combined.json')),stdout=log,stderr=subprocess.STDOUT)
    time.sleep(5)
    for settings in [[-60,120,12000,0],[0,80,8000,1],original_audio]:
        apply(3,settings);deadline=time.monotonic()+3
        while True:
            d=get(3)
            if d['applied']==settings and d['flags']&1:break
            assert time.monotonic()<deadline,('Preset not applied',d)
            time.sleep(.2)
        print('Live preset applied:',settings,flush=True)
        time.sleep(2)
    apply(4,0);disabled_at=time.monotonic()
    frozen=fetch('diagnostics-at-disable.log')
    print('Diagnostics disabled; checking log stays unchanged across a snapshot interval.',flush=True)
    while child.poll() is None:time.sleep(1)
    assert child.returncode==0,child.returncode
    child=None;log.close()
    while time.monotonic()-disabled_at<65:time.sleep(1)
    later=fetch('diagnostics-after-disabled-interval.log')
    assert frozen==later,'Diagnostics grew while disabled'
    fetch('post-readback-usb-counters.log',1)
    final_audio=get(3);final_diag=get(4)
    assert final_audio['requested']==original_audio and not final_audio['flags']&2
    assert final_diag['enabled']==0 and final_diag['saved']==0 and not final_diag['flags']&2
    (OUT/'uvc-test-result.json').write_text(json.dumps({'initial_audio':original_audio,'initial_diagnostics':original_diag,'live_presets_applied':True,'diagnostics_disabled_elapsed_s':time.monotonic()-disabled_at,'disabled_log_bytes':len(frozen),'disabled_log_sha256':hashlib.sha256(frozen).hexdigest(),'log_unchanged':True,'save_tested':False,'final_audio':final_audio,'final_diagnostics':final_diag},indent=2))
    print('PASS: live tuning, restored defaults, diagnostics on/off, frozen log and saved-off state.',flush=True)
finally:
    if child is not None and child.poll() is None:
        child.terminate()
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait()
    try:
        if original_audio is not None:apply(3,original_audio)
        if original_diag is not None:apply(4,original_diag)
    finally:u.close()
