from pathlib import Path
import hashlib,stat,struct
old=Path('/private/tmp/pisight-transport-diag/root')
new=Path('/private/tmp/pisight-coalesced-fix/root')
export=Path('/private/tmp/pisight-coalesced-fix/export')
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
assert changes==[],changes
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
oldimage=Path('diagnostics/sdcard-transport-diagnostics.img').read_bytes()
oldstart=u32(oldimage,446+8)*512
oldboot=oldimage[oldstart:]
oldfiles,newfiles=fat_files(oldboot),fat_files((export/'boot.vfat').read_bytes())
bootchanges=[name for name in sorted(oldfiles.keys()|newfiles.keys()) if oldfiles.get(name)!=newfiles.get(name)]
assert bootchanges==['ZIMAGE'],bootchanges
print('Boot file changes:',bootchanges)
output=Path('diagnostics/sdcard-coalesced-usb-fix.img')
output.write_bytes(data)
print('Verified packaged kernel and rootfs')
print('Image:',output.resolve(),len(data),'bytes')
print('SHA256:',hashlib.sha256(data).hexdigest())
