#!/usr/bin/env python3
"""Combine existing verified kernel/boot and shutter rootfs; regular files only."""
from pathlib import Path
import hashlib,struct
root=Path(__file__).resolve().parent
shutter=root/'sdcard-shutter-switch.img'
sof=root/'sdcard-audio-sof.img'
expected={shutter:'5634e3a8699b2944ebd9fd25fc42c27435c79a61ceed59a215c25b3f258c8a51',sof:'4e24ecde63ef34d3844cfee556c1c0c2906a68ccde075f13e81c7a087394f89a'}
for p,sha in expected.items():
    assert p.is_file() and not p.is_symlink(),p
    assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,p
old=shutter.read_bytes();new=bytearray(old);source=sof.read_bytes()
def partition(image,index):
    assert image[510:512]==b'\x55\xaa'
    entry=446+index*16
    return struct.unpack_from('<II',image,entry+8)
boot_start,boot_size=partition(old,0)
assert (boot_start,boot_size)==partition(source,0)
assert old[446:462]==source[446:462]
assert boot_start+boot_size<=partition(old,1)[0]
start,end=boot_start*512,(boot_start+boot_size)*512
new[start:end]=source[start:end]
# Everything except the boot partition remains byte-identical to the shutter image.
assert new[:start]==old[:start] and new[end:]==old[end:]
export=Path('/private/tmp/pisight-audio-sof-shutter/export');export.mkdir(parents=True,exist_ok=True)
(export/'sdcard.img').write_bytes(new)
(export/'boot.vfat').write_bytes(source[start:end])
root_start,root_size=partition(old,1)
rootfs=Path('/private/tmp/pisight-shutter-switch/export/rootfs.squashfs').read_bytes()
assert len(rootfs)<=root_size*512
assert old[root_start*512:root_start*512+len(rootfs)]==rootfs
(export/'rootfs.squashfs').write_bytes(rootfs)
kernel=Path('/private/tmp/pisight-audio-sof/export/zImage').read_bytes()
assert hashlib.sha256(kernel).hexdigest()=='964de3e23c6e030d9b72f96cee7a135df537fde63d90dc8837d1281e0f0259ff'
(export/'zImage').write_bytes(kernel)
(export/'SHA256SUMS').write_text(''.join(hashlib.sha256((export/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ['sdcard.img','boot.vfat','rootfs.squashfs','zImage']))
print('Combined verified images:',len(new),'bytes')
print('Export:',export)
