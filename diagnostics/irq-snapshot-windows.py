#!/usr/bin/env python3
"""Compare cumulative IRQ instrumentation across saved target snapshots.

Snapshot header times bracket slow shell collection, not atomic reads.
Percentages are approximate and include diagnostic overhead.
"""
import argparse, json, re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('log',type=Path)
a=p.parse_args()
rows=[]
for block in re.split(r'===== ',a.log.read_text(errors='replace'))[1:]:
    header=re.match(r'(.*?) at uptime ([\d.]+)',block)
    if not header: continue
    row={'uptime':float(header[2]),'label':header[1]}
    for kind in ('irq_causes','irq_work','irq_coverage'):
        line=re.search(r'^'+kind+r' (.+)$',block,re.M)
        if line:
            row[kind]={k:int(v,0) for k,v in (word.split('=',1) for word in line[1].split())}
    row['endpoints']={}
    for line in re.findall(r'^irq_endpoint (.+)$',block,re.M):
        fields={k:int(v,0) for k,v in (word.split('=',1) for word in line.split())}
        row['endpoints'][str(fields.pop('ep'))]=fields
    cpu=re.search(r'^cpu  (.+)$',block,re.M)
    if cpu:row['cpu']=list(map(int,cpu[1].split()))
    if 'irq_work' in row:rows.append(row)
windows=[]
for prev,cur in zip(rows,rows[1:]):
    elapsed=cur['uptime']-prev['uptime']
    if elapsed<=0:continue
    window={'start':prev['uptime'],'end':cur['uptime'],'seconds':elapsed}
    for kind in ('irq_causes','irq_work','irq_coverage'):
        # A lifetime maximum is not additive.
        window[kind]={k:cur[kind][k]-prev[kind].get(k,0) for k in cur[kind] if k!='handler_max_ns'}
    for kind,key in [('irq_work','entries'),('irq_causes','incomplete'),('irq_work','incomplete_only')]:
        window[key+'_per_second']=window[kind][key]/elapsed
    window['gadget_handler_percent']=window['irq_work']['handler_ns']/1e9/elapsed*100
    window['endpoint_rates']={}
    for ep,counts in cur['endpoints'].items():
        old=prev['endpoints'].get(ep,{})
        window['endpoint_rates'][ep]={k:(v-old.get(k,0))/elapsed for k,v in counts.items()}
    if 'cpu' in prev and 'cpu' in cur:
        delta=[v-o for v,o in zip(cur['cpu'],prev['cpu'])]
        total=sum(delta)
        if total:window['cpu_busy_percent']=100*(total-delta[3]-delta[4])/total
    windows.append(window)
if not rows:p.error('No target snapshots with patch0007 IRQ evidence.')
print(json.dumps({'snapshots':rows,'windows':windows,'limits':__doc__},indent=2))
