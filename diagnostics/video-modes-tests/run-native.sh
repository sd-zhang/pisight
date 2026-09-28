#!/bin/sh
# From repository root. Optional argument: fully patched uvc-gadget source tree.
set -eu
work=$(mktemp -d "${TMPDIR:-/tmp}/pisight-video-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
export STORE_CALLS_PATH="$work/store-calls"
cat > "$work/store-fixture" <<'HELPER'
#!/bin/sh
printf '%s\n' "$*" >> "$STORE_CALLS_PATH"
sleep 0.05
exit "${TEST_STORE_FAIL:-0}"
HELPER
chmod +x "$work/store-fixture"
for source in diagnostics/video-modes-tests/control.c diagnostics/audio-controls-tests/control.c; do
    cc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=undefined \
        -Iwebcampi/package/pisight-mic \
        "-DAUDIO_RUNTIME_PATH=\"$work/audio\"" \
        "-DDIAGNOSTICS_RUNTIME_PATH=\"$work/diagnostics\"" \
        "-DCONFIG_STORE_PATH=\"$work/store-fixture\"" \
        "-DSTORE_CALLS_PATH=\"$STORE_CALLS_PATH\"" \
        "$source" -o "$work/test"
    "$work/test"
done
if [ "$#" -gt 0 ]; then
    python3 diagnostics/audio-controls-tests/check-routing.py "$1"
    python3 diagnostics/audio-controls-tests/check-descriptor.py "$1/scripts/uvc-gadget.sh"
fi
