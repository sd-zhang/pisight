#!/usr/bin/env python3
from pathlib import Path
import re,json,statistics,hashlib,argparse
parser=argparse.ArgumentParser()
parser.add_argument('log',nargs='?',default='diagnostics/target-transport-diagnostics.log')
parser.add_argument('--output',default='diagnostics/target-transport-summary.json')
args=parser.parse_args()
p=Path(args.log);text=p.read_text()
blocks=re.split(r'microphone diagnostic uptime=',text)[1:]
rows=[]
for block in blocks:
    head=re.match(r'([\d.]+) pid=(\d+) trigger=(\S+)',block)
    if not head:continue
    # End this diagnostic at its final CPU frequency line, before other snapshots.
    freq=re.search(r'/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq\n(\d+)',block)
    assert freq
    block=block[:freq.end()]
    delays=re.findall(r'^delay\s*:\s*(\d+)',block,re.M)
    assert len(delays)==2
    stat=re.search(r'^\d+ \(alsaloop\) (.+)$',block,re.M).group(1).split()
    rows.append(dict(uptime=float(head[1]),pid=int(head[2]),trigger=head[3],capture_frames=int(delays[0]),playback_frames=int(delays[1]),combined_ms=sum(map(int,delays))/48,cpu_ticks=int(stat[11])+int(stat[12]),frequency_khz=int(freq[1])))
periodic=[r for r in rows if r['trigger']=='periodic']
sessions=[]
for pid in sorted(set(r['pid'] for r in periodic)):
    series=[r for r in periodic if r['pid']==pid];a,b=series[0],series[-1]
    sessions.append(dict(pid=pid,snapshots=len(series),elapsed=b['uptime']-a['uptime'],cpu_ticks=b['cpu_ticks']-a['cpu_ticks'],cpu_percent_user_hz_100=100*(b['cpu_ticks']-a['cpu_ticks'])/100/(b['uptime']-a['uptime'])))
result=dict(log_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),periodic_snapshots=len(periodic),alsa_combined_ms=dict(min=min(r['combined_ms'] for r in periodic),max=max(r['combined_ms'] for r in periodic),median=statistics.median(r['combined_ms'] for r in periodic)),cpu_sessions=sessions,snapshots=rows,limits='ALSA readings are sequential, not simultaneous; exclude userspace and host queues, not acoustic latency. CPU ticks use Linux ARM USER_HZ=100.')
Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='snapshots'},indent=2))
