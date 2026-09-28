#!/usr/bin/env python3
"""Execute actual settings/init scripts under target-configured host BusyBox.
Usage: check-settings-integration.py BUSYBOX HOST_JQ WEBCAMPI_ROOT
All device, mount, boot and daemon endpoints are replaced with temp fixtures.
Real jq, shell control flow and environment inheritance are exercised.
"""
import json, os, pathlib, subprocess, sys, tempfile, time
B, J, W = map(pathlib.Path, sys.argv[1:])
assert B.is_file() and J.is_file(), 'BusyBox and jq executables must exist'
O = W / 'board/raspberrypizero/rootfs-overlay'
with tempfile.TemporaryDirectory(prefix='pisight-settings-test-') as d:
    root = pathlib.Path(d)
    for folder in ['boot', 'bin', 'run', 'etc/isight', 'etc/default', 'tmp']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root/'device').touch()
    (root/'mounts').write_text(f'device {root}/boot vfat ro 0 0\n')
    (root/'etc/isight/config.default.json').write_bytes((O/'etc/isight/config.default.json').read_bytes())
    (root/'bin/sh').symlink_to(B)
    env = {k:v for k,v in os.environ.items() if not k.startswith('ISIGHT_')}
    env['PATH'] = str(root/'bin') + ':' + env['PATH']
    def executable(name, content):
        p=root/'bin'/name; p.write_text(content); p.chmod(0o755); return p
    executable('mount', f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{root}/mount-calls"\n[ "$PISIGHT_TEST_RO_FAIL" != 1 ] || [ "$2" != remount,ro ]\n')
    executable('sync', '#!/bin/sh\nexit 0\n')
    executable('isight-logo', '#!/bin/sh\nexit 0\n')
    executable('jq', f'#!/bin/sh\n[ -z "$PISIGHT_TEST_JQ_FAIL" ] || exit 1\nexec "{J}" "$@"\n')
    def fixture(source):
        text=pathlib.Path(source).read_text()
        for a,b in [('/proc/mounts',str(root/'mounts')),('/dev/mmcblk0p1',str(root/'device')),
                    ('/etc/isight',str(root/'etc/isight')),('/etc/default',str(root/'etc/default')),
                    ('/sys/kernel',str(root/'sys/kernel')),('/var/run',str(root/'run')),
                    ('/run/isight.env',str(root/'run/isight.env')),
                    ('/run/pisight-diagnostics',str(root/'run/pisight-diagnostics')),('/usr/local/bin',str(root/'bin')),
                    ('/sbin/reboot',str(root/'bin/reboot')),('/usr/bin/',str(root/'bin')+'/'),('/boot',str(root/'boot'))]:
            text=text.replace(a,b)
        # Route diagnostic log output too, without re-replacing fixture paths.
        for name in ['isight-config-apply.log','uvc-setup.log','uvc-gadget.log']:
            text=text.replace('/tmp/'+name,str(root/'tmp'/name))
        text=text.replace('#!/bin/sh',f'#!{B} sh',1)
        return text
    subprocess.run(['cc','-std=c99','-O2',f'-DCONFIG_LOCK_PATH="{root}/run/config.lock"',
                    str(W/'package/pisight-mic/config-lock.c'),'-o',str(root/'bin/isight-config-lock')],check=True)
    apply=executable('isight-config-apply',fixture(O/'usr/bin/isight-config-apply'))
    save=executable('isight-config-store',fixture(O/'usr/bin/isight-config-store'))
    executable('uvc-gadget.sh',f'#!/bin/sh\nenv > "{root}/gadget-environment.tmp"; mv "{root}/gadget-environment.tmp" "{root}/gadget-environment"\n')
    executable('uvc-gadget',f'#!/bin/sh\nenv > "{root}/camera-environment.tmp"; mv "{root}/camera-environment.tmp" "{root}/camera-environment"\n')
    config={'resolutions':['640x480'], 'fov':50, 'ev':-1.2, 'logo_light':'off', 'quality':41, 'microphone':False, 'extra':'preserve'}
    expected={'ISIGHT_RESOLUTIONS':'640x480 ', 'ISIGHT_FOV':'50', 'ISIGHT_EV':'-1.2', 'ISIGHT_LOGO':'off', 'ISIGHT_QUALITY':'41', 'ISIGHT_MICROPHONE':'off'}
    failures=[]
    for original in [W/'package/uvc-gadget/S60uvc-gadget', O/'etc/init.d/S60uvc-gadget']:
        (root/'boot/isight.json').write_text(json.dumps(config))
        for name in ['gadget-environment','camera-environment']:
            (root/name).unlink(missing_ok=True)
        init=executable('init-fixture',fixture(original))
        p=subprocess.run([str(B),'sh',str(init),'start'],env=env,capture_output=True,text=True,timeout=10)
        deadline=time.monotonic()+3
        while not (root/'camera-environment').exists() and time.monotonic()<deadline: time.sleep(.01)
        for name in ['gadget-environment','camera-environment']:
            actual=dict(line.split('=',1) for line in (root/name).read_text().splitlines() if '=' in line)
            missing={k:(v,actual.get(k)) for k,v in expected.items() if actual.get(k)!=v}
            if missing: failures.append((str(original),name,missing,p.stderr))
        print(('FAIL' if failures else 'PASS')+': '+str(original.relative_to(W))+' child settings')
    assert not failures, failures
    p=subprocess.run([str(B),'sh',str(save),'60','15','activity','1'],env=env,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    saved=json.loads((root/'boot/isight.json').read_text())
    assert saved==dict(config,fov=60,ev=1.5,logo_light='activity',microphone=True),saved
    assert not list((root/'boot').glob('.isight.*'))
    assert (root/'mount-calls').read_text().splitlines()[-1]==f'-o remount,ro {root}/boot'
    print('PASS: persistent save changes requested fields and preserves others')
    before=(root/'boot/isight.json').read_bytes()
    p=subprocess.run([str(B),'sh',str(save),'60','15','activity','0'],env=dict(env,PISIGHT_TEST_JQ_FAIL='1'),capture_output=True,text=True)
    assert p.returncode!=0
    assert (root/'boot/isight.json').read_bytes()==before
    assert not list((root/'boot').glob('.isight.*'))
    assert (root/'mount-calls').read_text().splitlines()[-1]==f'-o remount,ro {root}/boot'
    print('PASS: failed JSON update preserves original and cleans up temporary file/mount')

    for args, field, expected_value in [
        (['--audio','60','120','12000','0'],'audio',{'gain_db':6,'highpass_hz':120,'lowpass_hz':12000,'bypass':False}),
        (['--diagnostics','1'],'diagnostics',True)]:
        before=json.loads((root/'boot/isight.json').read_text())
        p=subprocess.run([str(B),'sh',str(save),*args],env=env,capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        after=json.loads((root/'boot/isight.json').read_text())
        assert after==dict(before,**{field:expected_value})
    p=subprocess.run([str(B),'sh',str(apply)],env=env,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert 'ISIGHT_AUDIO="60 120 12000 0"' in (root/'run/isight.env').read_text()
    assert (root/'run/pisight-diagnostics').read_text()=='1\n'
    print('PASS: audio/diagnostics save preserves camera fields; boot restores values')
    saved=(root/'boot/isight.json').read_bytes()
    for args in [['--audio','241','80','8000','0'],['--audio','0','501','8000','0'],['--audio','0','80','8501','0'],['--audio','0','80','8000','2'],['--diagnostics','2']]:
        p=subprocess.run([str(B),'sh',str(save),*args],env=env,capture_output=True,text=True)
        assert p.returncode!=0 and (root/'boot/isight.json').read_bytes()==saved
    print('PASS: invalid audio/diagnostics cannot alter persisted config')
    # Saving a video set changes only the advertised list, and boot consumes it.
    presets={1:['1280x720'],2:['1920x1080'],3:['1280x720','1920x1080'],
             4:['1280x960'],5:['1280x720','1280x960'],6:['1920x1080','1280x960'],
             7:['1280x720','1920x1080','1280x960']}
    for mask,modes in presets.items():
        before=json.loads((root/'boot/isight.json').read_text())
        p=subprocess.run([str(B),'sh',str(save),'--resolutions',str(mask)],env=env,capture_output=True,text=True)
        assert p.returncode==0, p.stderr
        assert json.loads((root/'boot/isight.json').read_text())==dict(before,resolutions=modes)
        subprocess.run([str(B),'sh',str(apply)],env=env,check=True,capture_output=True)
        assert 'ISIGHT_RESOLUTIONS="'+' '.join(modes)+' "' in (root/'run/isight.env').read_text()
    print('PASS: all seven video sets persist without changing other settings and reload at boot')
    saved=(root/'boot/isight.json').read_bytes()
    for mask in ['0','8','255','-1','01','','abc']:
        for op in ['--resolutions','--resolutions-reboot']:
            p=subprocess.run([str(B),'sh',str(save),op,mask],env=env,capture_output=True,text=True)
            assert p.returncode!=0 and (root/'boot/isight.json').read_bytes()==saved
    # Only the external reboot endpoint is mocked. Assert disk contents and RO
    # transition *at invocation*, not just that the mock command was called.
    executable('reboot', f'''#!/bin/sh
cp "{root}/boot/isight.json" "{root}/reboot-config"
tail -n 1 "{root}/mount-calls" > "{root}/reboot-mount"
exit "${{PISIGHT_TEST_REBOOT_FAIL:-0}}"
''')
    started=time.monotonic()
    p=subprocess.run([str(B),'sh',str(save),'--resolutions-reboot','1'],env=env,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert time.monotonic()-started>=1, 'allow control transfer to complete before reboot'
    assert json.loads((root/'reboot-config').read_text())['resolutions']==['1280x720']
    assert (root/'reboot-mount').read_text().strip()==f'-o remount,ro {root}/boot'
    (root/'reboot-config').unlink()
    p=subprocess.run([str(B),'sh',str(save),'--resolutions-reboot','2'],env=dict(env,PISIGHT_TEST_JQ_FAIL='1'),capture_output=True,text=True)
    assert p.returncode!=0 and not (root/'reboot-config').exists()
    p=subprocess.run([str(B),'sh',str(save),'--resolutions-reboot','2'],env=dict(env,PISIGHT_TEST_RO_FAIL='1'),capture_output=True,text=True)
    assert p.returncode!=0 and not (root/'reboot-config').exists()
    p=subprocess.run([str(B),'sh',str(save),'--resolutions-reboot','2'],env=dict(env,PISIGHT_TEST_REBOOT_FAIL='1'),capture_output=True,text=True)
    assert p.returncode!=0 and (root/'reboot-config').exists()
    saved=(root/'boot/isight.json').read_bytes()
    print('PASS: reboot follows successful save/remount and delay; save failures never reboot; reboot failures surface')
    # Kernel lock serializes camera and audio writers and survives neither crash nor exit.
    import fcntl
    with (root/'run/config.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        p=subprocess.run([str(B),'sh',str(save),'--diagnostics','0'],env=env,capture_output=True,text=True)
        assert p.returncode!=0 and (root/'boot/isight.json').read_bytes()==saved
    print('PASS: concurrent save rejected without overwriting JSON')

    for bad in [{'gain_db':25}, {'gain_db':0,'highpass_hz':19,'lowpass_hz':8000,'bypass':False}, 'bad', {'gain_db':0,'highpass_hz':80,'lowpass_hz':1000.5,'bypass':False}]:
        (root/'boot/isight.json').write_text(json.dumps(dict(config,audio=bad,diagnostics='true')))
        p=subprocess.run([str(B),'sh',str(apply)],env=env,capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        assert 'ISIGHT_AUDIO="0 80 8000 0"' in (root/'run/isight.env').read_text()
        assert (root/'run/pisight-diagnostics').read_text()=='0\n'
    print('PASS: malformed/missing settings fall back to band-pass default and diagnostics off')
