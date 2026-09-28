#!/usr/bin/env python3
"""Read saved target snapshots and reconcile cumulative USB completion counters."""
from pathlib import Path
import re,json,hashlib

def summarize(path):
    text=path.read_text()
    counters={}
    samples={}
    for ep,reason,missed,payload,burst in re.findall(r'^(ep\din) (start|disabled|out-token|nak) missed=(\d+) payload=(\d+) max_burst=(\d+)$',text,re.M):
        counters.setdefault(ep,{})[reason]=dict(missed=int(missed),payload=int(payload),max_burst=int(burst))
    for ep,reason,kind,fields in re.findall(r'^(ep\din) (start|disabled|out-token|nak) (first_burst|last_burst|worst_burst) (.+)$',text,re.M):
        samples.setdefault(ep,{}).setdefault(reason,{})[kind]={k:int(v,0) for k,v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)',fields)}
    streams={}
    for timestamp,payload,empty,other in re.findall(r'\[\s*([\d.]+)\].*USB transfer summary: missed_payload=(\d+) missed_empty=(\d+) other_errors=(\d+)',text):
        streams[timestamp]=dict(payload=int(payload),empty=int(empty),other=int(other))
    totals={k:sum(v[k] for v in streams.values()) for k in ['payload','empty','other']}
    assert totals['payload']==sum(v['payload'] for v in counters['ep1in'].values())
    assert totals['empty']==sum(v['missed']-v['payload'] for v in counters['ep1in'].values())
    snapshots=[]
    for block in re.split(r'===== ',text)[1:]:
        head=re.match(r'(.*?) at uptime ([\d.]+)',block)
        if not head:continue
        cpu=re.search(r'^cpu  (.+)',block,re.M)
        irq=re.search(r'^ *\d+:\s+(\d+).*20980000\.usb',block,re.M)
        snapshots.append(dict(uptime=float(head[2]),cpu=list(map(int,cpu[1].split())),usb_irqs=int(irq[1])))
    windows=[]
    for a,b in zip(snapshots,snapshots[1:]):
        d=[y-x for x,y in zip(a['cpu'],b['cpu'])];total=sum(d)
        windows.append(dict(start=a['uptime'],end=b['uptime'],cpu_busy_percent=100*(total-d[3]-d[4])/total,usb_irqs_per_second=(b['usb_irqs']-a['usb_irqs'])/(b['uptime']-a['uptime'])))
    return dict(file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),counters=counters,samples=samples,stream_totals=totals,streams=streams,cpu_windows=windows)

result={name:summarize(Path(path)) for name,path in [('before','diagnostics/target-transport-diagnostics.log'),('after','diagnostics/target-coalesced-fix.log')]}
Path('diagnostics/coalesced-target-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
for name,r in result.items():
    print(name,'stream totals',r['stream_totals'])
    print('CPU windows',json.dumps(r['cpu_windows']))
print('PASS: UVC and endpoint payload/empty totals reconcile in both logs')
