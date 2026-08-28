#!/usr/bin/env bash
set -euo pipefail

cd ~/git/pisight/webcampi

SCRIPT="buildroot/output/build/uvc-gadget-v0.4.4/scripts/uvc-gadget.sh"

python3 <<'PY'
from pathlib import Path
p = Path("buildroot/output/build/uvc-gadget-v0.4.4/scripts/uvc-gadget.sh")
s = p.read_text()

start = s.index('        create_frame $FUNCTION 640 480 uncompressed')
end_marker = '        create_frame $FUNCTION 1920 1080 mjpeg m "333333\n416667\n500000\n666666\n1000000\n1333333\n2000000\n"\n'
end = s.index(end_marker, start) + len(end_marker)

replacement = '''        create_frame $FUNCTION 640 480 mjpeg m "333333
416667
"

        create_frame $FUNCTION 1280 720 mjpeg m "333333
416667
"

        create_frame $FUNCTION 1920 1080 mjpeg m "333333
416667
"
'''

p.write_text(s[:start] + replacement + s[end:])
PY

echo "Updated modes:"
grep -A14 -B2 'create_frame \$FUNCTION 640 480 mjpeg' "$SCRIPT"

CC=gcc-14 CXX=g++-14 HOSTCC=gcc-14 HOSTCXX=g++-14 \
make -C buildroot uvc-gadget-rebuild

CC=gcc-14 CXX=g++-14 HOSTCC=gcc-14 HOSTCXX=g++-14 \
make -C buildroot

# Keep the Pi Zero kernel filename correct if Buildroot refreshed this file.
sed -i 's/^kernel=Image$/kernel=zImage/' \
  buildroot/output/images/rpi-firmware/config.txt

make -C buildroot target-post-image

echo
echo "Done:"
ls -lh buildroot/output/images/sdcard.img
