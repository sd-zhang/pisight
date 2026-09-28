#!/usr/bin/env python3
"""Summarize diagnostic evidence without inferring unobserved USB token timing."""
import argparse
import json
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('log',type=Path)
args=parser.parse_args()
text=args.log.read_text(errors='replace')
state={}
endpoints={}
samples={}
for line in text.splitlines():
    words=line.split()
    if not words or words[0] not in ('irq_causes','irq_work','irq_coverage','irq_endpoint','irq_decision'):
        continue
    fields={}
    for word in words[1:]:
        if '=' in word:
            key,value=word.split('=',1)
            fields[key]=int(value,0)
    if words[0]=='irq_endpoint':
        endpoints[str(fields['ep'])]=fields
    elif words[0]=='irq_decision':
        samples[(fields['ep'],fields['session'],fields['ns'])]=fields
    else:
        state[words[0]]=fields
if not state:
    parser.error('No patch0007 interrupt evidence found; this log cannot test the hypothesis.')
work=state.get('irq_work',{})
if work.get('entries'):
    state['gadget_handler_mean_us']=work['handler_ns']/work['entries']/1000
    state['gadget_handler_max_us']=work['handler_max_ns']/1000
for sample in samples.values():
    delta=(sample['arm_target']-sample['arm_before'])&16383
    sample['arm_observed_before_target']=(sample['arm_before']==sample['arm_after'] and 0<delta<8192 and sample['arm_target']==sample['target'])
    sample['current_target_selected_before_eopf_bound']=(bool(sample['before_eopf']) and sample['live']==sample['target'])
state['endpoints']=endpoints
state['decisions']=list(samples.values())
state['interpretation']='Conditional timing evidence only. No assertion of audio origin, FIFO readiness, pre-token disable, or performance causation. Handler time excludes common IRQ handling and includes instrumentation.'
print(json.dumps(state,indent=2))
