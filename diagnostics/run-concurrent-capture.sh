#!/bin/bash
# Host-only capture. Never mounts, flashes, or writes a physical drive.
set -eu
TASK_ROOT=$(cd "$(dirname "$0")/.." && pwd)
CAPTURE_OUT=${1:-"$TASK_ROOT/diagnostics/capture-$(date +%Y%m%d-%H%M%S)"}
FFMPEG=${FFMPEG:-/opt/homebrew/bin/ffmpeg}
export PISIGHT_MIC_NAME=${PISIGHT_MIC_NAME:-"iSight Microphone"}
video_pid=
audio_pid=

cleanup() {
	[ -z "$video_pid" ] || kill "$video_pid" 2>/dev/null || true
	[ -z "$audio_pid" ] || kill "$audio_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p "$CAPTURE_OUT"
command -v swiftc >/dev/null
[ -x "$FFMPEG" ]
swiftc "$TASK_ROOT/diagnostics/native-capture-timing.swift" -o "$CAPTURE_OUT/capture-timing"

mark() {
	python3 - "$1" >> "$CAPTURE_OUT/events.jsonl" <<'PY'
import json, sys, time
print(json.dumps({'event': sys.argv[1], 'unix_time': time.time()}))
PY
}

echo "Capturing 720p video for 150 seconds, with the USB microphone open for the middle 120 seconds."
mark video_start
PISIGHT_RESULT="$CAPTURE_OUT/video-toggle.json" "$CAPTURE_OUT/capture-timing" 150 --video-only > "$CAPTURE_OUT/video-toggle.log" 2>&1 &
video_pid=$!
sleep 15
kill -0 "$video_pid" 2>/dev/null || { echo "Video probe exited; inspect $CAPTURE_OUT/video-toggle.log"; exit 1; }
mark microphone_open
"$FFMPEG" -nostdin -hide_banner -f avfoundation -i ":$PISIGHT_MIC_NAME" -t 120 -ac 1 -ar 48000 -c:a pcm_s16le "$CAPTURE_OUT/microphone.wav" > "$CAPTURE_OUT/microphone.log" 2>&1 &
audio_pid=$!
if wait "$audio_pid"; then audio_pid=; else audio_pid=; exit 1; fi
mark microphone_closed
if wait "$video_pid"; then video_pid=; else video_pid=; exit 1; fi
mark video_closed

echo "Checking simultaneous native video/audio capture for 20 seconds."
PISIGHT_RESULT="$CAPTURE_OUT/combined.json" "$CAPTURE_OUT/capture-timing" 20 > "$CAPTURE_OUT/combined.log" 2>&1
mark combined_closed
/usr/bin/log show --style compact --last 5m --predicate 'process == "UVCAssistant"' > "$CAPTURE_OUT/host-usb.log" 2>&1 || true
echo "Capture finished. Allowing 70 seconds for the Pi's next saved diagnostic snapshot."
sleep 70
mark target_save_window_elapsed
if python3 "$TASK_ROOT/diagnostics/read-usb-diagnostics.py" --source log --output "$CAPTURE_OUT/target.log" > "$CAPTURE_OUT/target-readback.log" 2>&1; then
	mark target_log_retrieved
	python3 "$TASK_ROOT/diagnostics/read-usb-diagnostics.py" --source usb --output "$CAPTURE_OUT/target-usb-counters.log" >> "$CAPTURE_OUT/target-readback.log" 2>&1 || true
	echo "Target diagnostic log retrieved over USB."
else
	echo "USB log readback unavailable; inspect $CAPTURE_OUT/target-readback.log"
fi
echo "Results: $CAPTURE_OUT"
