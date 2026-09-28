#!/usr/bin/env python3
"""Compare aggregate endpoint counters; first/last/worst samples are not totals."""
import json,re,sys
from pathlib import Path
def counters(path):
    result={}
    for ep,kind,fields in re.findall(r'^(ep\din) (arm|start|disabled|out-token|nak) (.*)$',Path(path).read_text(),re.M):
        if kind!='arm' and not fields.startswith('missed='):
            continue
        result[ep+' '+kind]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',fields)}
    return result
a,b=map(counters,sys.argv[1:3])
delta={k:{f:v-a[k].get(f,0) for f,v in vals.items() if f not in ('max_burst','lateness_max_ns','callback_max_ns')} for k,vals in b.items()}
print(json.dumps(delta,indent=2))
