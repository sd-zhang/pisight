from pathlib import Path
import re,json
p=Path(__file__).parent
text=(p/'target.log').read_text()
blocks=re.split(r'^===== (.*?) at uptime ([\d.]+).*?=====\n',text,flags=re.M)
rows=[]
def fields(line):return {k:int(v,0) for k,v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)',line)}
for i in range(1,len(blocks),3):
 label,uptime,b=blocks[i:i+3]
 section=b.split('--- CPU, interrupts, and thread accounting ---')[1].split('--- microphone bridge ---')[0]
 cpu=list(map(int,re.search(r'^cpu\s+(.*)$',section,re.M)[1].split()))
 threads={}
 for proc,tid,s in re.findall(r'^/proc/(\d+)/task/(\d+)/stat\n([^\n]+)',section,re.M):
  name=re.search(r'\((.*?)\)',s)[1];values=s[s.rindex(')')+2:].split()
  threads[proc+'/'+tid]={'name':name,'user':int(values[11]),'system':int(values[12])}
 for proc,tid,ns in re.findall(r'^/proc/(\d+)/task/(\d+)/schedstat\n(\d+)',section,re.M):threads[proc+'/'+tid]['runtime_ns']=int(ns)
 counters=b.split('--- USB recovery counters (cumulative since boot) ---')[1].split('--- CPU frequency ---')[0]
 row={'label':label,'uptime':float(uptime),'cpu':cpu,'threads':threads,'pcm_running':len(re.findall(r'^state:\s+RUNNING',b.split('--- processes ---')[0],re.M))==2}
 for name in ['irq_causes','irq_work']:
  row[name]=fields(re.search('^'+name+' (.*)$',counters,re.M)[1])
 rows.append(row)
windows=[]
for a,b in zip(rows,rows[1:]):
 secs=b['uptime']-a['uptime'];cpu=[y-x for x,y in zip(a['cpu'],b['cpu'])];total=sum(cpu[:8])
 w={'start':a['uptime'],'end':b['uptime'],'seconds':secs,'both_snapshots_pcm_running':a['pcm_running'] and b['pcm_running'],'cpu_busy_percent':100*(total-cpu[3]-cpu[4])/total,'irq_per_second':(b['irq_work']['entries']-a['irq_work']['entries'])/secs,'incomplete_per_second':(b['irq_causes']['incomplete']-a['irq_causes']['incomplete'])/secs,'handler_elapsed_percent':100*(b['irq_work']['handler_ns']-a['irq_work']['handler_ns'])/1e9/secs}
 costs=[]
 for key,t in b['threads'].items():
  if key in a['threads'] and 'runtime_ns' in t and 'runtime_ns' in a['threads'][key]:
   costs.append({'thread':key,'name':t['name'],'runtime_percent':100*(t['runtime_ns']-a['threads'][key]['runtime_ns'])/1e9/secs})
 w['threads']=sorted(costs,key=lambda x:-x['runtime_percent']);windows.append(w)
(p/'cpu-windows.json').write_text(json.dumps({'snapshots':rows,'windows':windows},indent=2))
print(json.dumps(windows,indent=2))
