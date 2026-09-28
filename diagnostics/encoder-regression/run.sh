#!/bin/sh
set -eu
src=${1:?actual uvc-gadget source directory required}
out=${2:-/tmp/encoder-regression}
c++ -std=c++17 -pthread -Wall -Wextra ${BASELINE:+-DBASELINE} -I"$src/lib" \
  "$(dirname "$0")/codec.cpp" "$src/lib/hw_mjpeg_encoder.cpp" \
  -Wl,--wrap=open -Wl,--wrap=mmap -Wl,--wrap=ioctl -Wl,--wrap=close -Wl,--wrap=munmap -o "$out"
failed=0
for mode in ok error input_error zero length offset index truncated small qout qcap dout dcap recover timeout cancel; do
 "$out" "$mode" || failed=1
done
exit "$failed"
