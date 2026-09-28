#!/usr/bin/env python3
"""Verify fixed-band-pass candidate, preserving the tested boot partition byte-for-byte."""
from pathlib import Path
import hashlib,stat,struct,re,subprocess
work=Path('/private/tmp/pisight-bandpass')
export=work/'export'
oldroot=Path('/private/tmp/pisight-camera-work/root')
newroot=work/'root'
baseline=Path('diagnostics/sdcard-camera-work.img').read_bytes()
sha=lambda data:hashlib.sha256(data).hexdigest()
assert sha(baseline)=='95ecfd3891d2462178578b7b4f1b33cbe9a2c4c2806867ecf481cb14bdbec267'
u16=lambda x,o:struct.unpack_from('<H',x,o)[0]
u32=lambda x,o:struct.unpack_from('<I',x,o)[0]
def inventory(root):
    out={}
    for p in root.rglob('*'):
        mode=stat.S_IMODE(p.lstat().st_mode);rel=str(p.relative_to(root))
        if p.is_symlink():out[rel]=('link',mode,p.readlink().as_posix())
        elif p.is_file():out[rel]=('file',mode,sha(p.read_bytes()))
    return out
before,after=inventory(oldroot),inventory(newroot)
changes=[k for k in sorted(before.keys()|after.keys()) if before.get(k)!=after.get(k)]
print('Root filesystem changes:',changes)
assert changes==['etc/asound.conf','usr/lib/alsa-lib/libasound_module_pcm_pisight_voice.so'],changes
assert not list(newroot.rglob('._*'))
for line in (export/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split();assert sha((export/name).read_bytes())==expected,name
for line in (export/'compiled-source-sha.txt').read_text().splitlines():
    expected,name=line.split()
    assert name in ('pisight-mic.c','pcm_pisight_voice.c','voice-filter.h','pisight-mic.mk')
    local=Path('webcampi/package/pisight-mic')/name
    assert sha(local.read_bytes())==expected,name
def fat_files(raw):
    sec=u16(raw,11); csec=raw[13]; res=u16(raw,14); nf=raw[16]
    entries=u16(raw,17); fs=u16(raw,22)
    root_off=(res+nf*fs)*sec
    ds=res+nf*fs+(entries*32+sec-1)//sec
    table=raw[res*sec:(res+fs)*sec]
    def chain(c):
        out=bytearray(); visited=set()
        while 2<=c<65528:
            assert c not in visited
            visited.add(c); pos=(ds+(c-2)*csec)*sec
            out.extend(raw[pos:pos+csec*sec]); c=u16(table,c*2)
        return bytes(out)
    result={}
    def walk(directory,prefix):
        for off in range(0,len(directory),32):
            e=directory[off:off+32]
            if not e or e[0]==0: break
            if e[0]==229 or e[11]==15 or e[11]&8 or e[0]==46: continue
            name=e[:8].decode().strip(); ext=e[8:11].decode().strip()
            path=prefix+name+('.'+ext if ext else '')
            data=chain(u16(e,26))
            if e[11]&16: walk(data,path+'/')
            else: result[path]=data[:u32(e,28)]
    walk(raw[root_off:root_off+entries*32],'')
    return result

data=bytearray((export/'sdcard.img').read_bytes())
root=(export/'rootfs.squashfs').read_bytes();boot=(export/'boot.vfat').read_bytes()
root_start=u32(data,446+16+8)*512
assert data[root_start:root_start+len(root)]==root
boot_start=u32(data,446+8)*512;boot_size=u32(data,446+12)*512
assert boot_start==u32(baseline,446+8)*512 and boot_size==u32(baseline,446+12)*512
assert len(boot)==boot_size and data[boot_start:boot_start+boot_size]==boot
oldboot=baseline[boot_start:boot_start+boot_size]
oldfiles,newfiles=fat_files(oldboot),fat_files(boot)
assert oldfiles==newfiles,'Unexpected boot file change'
assert newfiles['ZIMAGE']==(export/'zImage').read_bytes()
# File contents match; retain known-good FAT metadata too.
data[boot_start:boot_start+boot_size]=oldboot
assert data[boot_start:boot_start+boot_size]==oldboot
print('Boot partition and kernel unchanged from tested image')
out=Path('diagnostics/sdcard-bandpass.img');out.write_bytes(data)
(out.with_suffix('.img.sha256')).write_text(sha(data)+'  '+out.name+'\n')
print('Verified source hashes, exactly two root changes, packaged rootfs and unchanged boot/kernel')
print('Image:',out.resolve(),len(data),'bytes')
print('SHA256:',sha(data))
