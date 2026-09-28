from pathlib import Path
import hashlib,stat,struct
old=Path('/private/tmp/pisight-audit-fixes-root')
new=Path('/private/tmp/pisight-transport-diag/root')
export=Path('/private/tmp/pisight-transport-diag/export')
def inventory(root):
    out={}
    for p in root.rglob('*'):
        mode=stat.S_IMODE(p.lstat().st_mode); rel=str(p.relative_to(root))
        if p.is_symlink(): out[rel]=('link',mode,p.readlink().as_posix())
        elif p.is_file(): out[rel]=('file',mode,hashlib.sha256(p.read_bytes()).hexdigest())
    return out
a,b=inventory(old),inventory(new)
changes=[x for x in sorted(a.keys()|b.keys()) if a.get(x)!=b.get(x)]
print('Rootfs changed paths:',changes)
assert changes==['etc/init.d/S62pisight-diagnostic','usr/bin/pisight-mic'],changes
assert not list(new.rglob('._*'))
assert (new/'etc/init.d/S62pisight-diagnostic').read_bytes()==Path('webcampi/board/raspberrypizero/rootfs-overlay/etc/init.d/S62pisight-diagnostic').read_bytes()
assert (new/'etc/init.d/S62pisight-diagnostic').read_bytes()==Path('diagnostics/S62pisight-diagnostic').read_bytes()
assert b'microphone diagnostic uptime=' in (new/'usr/bin/pisight-mic').read_bytes()
for line in (export/'SHA256SUMS').read_text().splitlines():
    sha,name=line.split()
    assert hashlib.sha256((export/name).read_bytes()).hexdigest()==sha,name
data=(export/'sdcard.img').read_bytes()
u16=lambda x,o:struct.unpack_from('<H',x,o)[0]
u32=lambda x,o:struct.unpack_from('<I',x,o)[0]
root=(export/'rootfs.squashfs').read_bytes()
root_start=u32(data,446+16+8)*512
assert data[root_start:root_start+len(root)]==root
fat_start=u32(data,446+8)*512
boot=data[fat_start:]
sector=u16(boot,11); cluster_sectors=boot[13]; reserved=u16(boot,14); nfats=boot[16]
root_entries=u16(boot,17); total=u16(boot,19) or u32(boot,32); fat_sectors=u16(boot,22) or u32(boot,36)
root_sectors=(root_entries*32+sector-1)//sector
root_offset=(reserved+nfats*fat_sectors)*sector
data_sector=reserved+nfats*fat_sectors+root_sectors
clusters=(total-data_sector)//cluster_sectors
assert 4085<=clusters<65525, 'Verifier expects FAT16 boot filesystem'
fat=boot[reserved*sector:(reserved+fat_sectors)*sector]
directory=boot[root_offset:root_offset+root_entries*32]
entry=next(directory[i:i+32] for i in range(0,len(directory),32) if directory[i:i+11]==b'ZIMAGE     ')
cluster=u16(entry,26); size=u32(entry,28); kernel=bytearray(); seen=set()
while 2<=cluster<65528:
    assert cluster not in seen
    seen.add(cluster)
    off=(data_sector+(cluster-2)*cluster_sectors)*sector
    kernel.extend(boot[off:off+cluster_sectors*sector])
    cluster=u16(fat,cluster*2)
assert kernel[:size]==(export/'zImage').read_bytes(), 'Packaged kernel differs'
output=Path('diagnostics/sdcard-transport-diagnostics.img')
output.write_bytes(data)
print('Verified packaged kernel and rootfs')
print('Image:',output.resolve(),len(data),'bytes')
print('SHA256:',hashlib.sha256(data).hexdigest())
