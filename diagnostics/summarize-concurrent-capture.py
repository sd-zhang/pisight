#!/usr/bin/env python3
"""Summarize saved host measurements; does not open devices or infer acoustic latency."""
import array
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys
import wave
from zoneinfo import ZoneInfo

root = Path(sys.argv[1])
events = {e['event']: e['unix_time'] for e in
          map(json.loads, (root / 'events.jsonl').read_text().splitlines())}
video = json.loads((root / 'video-toggle.json').read_text())
combined = json.loads((root / 'combined.json').read_text())
log = (root / 'host-usb.log').read_text()
errors = []
for line in log.splitlines():
    if 'decode callback with error' in line:
        errors.append(datetime.fromisoformat(line[:23]).replace(
            tzinfo=ZoneInfo('America/Vancouver')).timestamp())

times = video['video_changed_frame_unix_times']
windows = {
    'before_microphone': (times[0] + 2, events['microphone_open'] - 2),
    'during_microphone': (events['microphone_open'] + 2, events['microphone_closed'] - 2),
    'after_microphone': (events['microphone_closed'] + 2, times[-1] - 2),
}
summary = {'events': events, 'stable_windows': {}}
for name, (start, end) in windows.items():
    frames = [t for t in times if start <= t <= end]
    summary['stable_windows'][name] = {
        'start_unix': start, 'end_unix': end, 'window_seconds': end - start,
        'changed_images': len(frames),
        'changed_fps': ((len(frames) - 1) / (frames[-1] - frames[0])
                        if len(frames) > 1 else None),
        'jpeg_decode_errors': sum(start <= t <= end for t in errors),
        'max_changed_image_gap_ms': max(
            ((b - a) * 1000 for a, b in zip(frames, frames[1:])), default=None),
    }
for name, report in [('video_toggle', video), ('combined', combined)]:
    summary[name] = {k: v for k, v in report.items()
                     if k != 'video_changed_frame_unix_times'}
summary['decoder_sessions'] = [
    {'completed': int(a), 'dropped': int(b), 'duration_ms': int(c)}
    for a, b, c in re.findall(r'invalidating decompression session: decoded (\d+) dropped (\d+) duration (\d+)', log)
]
with wave.open(str(root / 'microphone.wav')) as wav:
    assert wav.getsampwidth() == 2 and wav.getnchannels() == 1
    samples = array.array('h', wav.readframes(wav.getnframes()))
    if sys.byteorder != 'little':
        samples.byteswap()
    summary['raw_microphone'] = {
        'sample_rate': wav.getframerate(), 'samples': len(samples),
        'sample_seconds': len(samples) / wav.getframerate(),
        'minimum': min(samples), 'maximum': max(samples),
        'distinct_values': len(set(samples)),
        'rms': math.sqrt(sum(x * x for x in samples) / len(samples)),
    }
summary['limitations'] = [
    'Host timestamps and WAV continuity do not measure acoustic microphone delay.',
    'Target driver counters and active PCM buffering require the Pi log readback.',
    'Different scene/exposure between builds prevents attributing all FPS changes to code.',
    'Microphone event times bracket process launch/exit, not exact USB alternate-setting changes; stable windows trim two seconds.',
]
output = root / 'summary.json'
output.write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
