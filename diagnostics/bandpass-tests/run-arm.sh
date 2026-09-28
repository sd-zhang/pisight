#!/bin/sh
# Inside pisight-emulation:arm64 with the existing build volume at /work.
# Fixtures generated from the repository asound.conf; only hardware is replaced.
set -eu
export QEMU_LD_PREFIX=/work/bandpass/root
export ALSA_PLUGIN_DIR=/work/bandpass/plugins
export ALSA_CONFIG_PATH=/work/bandpass/asound.conf
cp "$QEMU_LD_PREFIX/usr/lib/alsa-lib/libasound_module_pcm_pisight_voice.so" "$ALSA_PLUGIN_DIR/"
run() { qemu-arm-static -cpu arm1176 "$@"; }
run /work/bandpass/filter-arm
run /work/bandpass/areas-arm
run /work/bandpass/capture-arm /work/bandpass/capture-17.s16 96000 17 48000 1 0
run /work/bandpass/capture-arm /work/bandpass/capture-1024.s16 96000 1024 48000 1 0
cmp /work/bandpass/capture-17.s16 /work/bandpass/capture-1024.s16
TEST_RESTART=1 run /work/bandpass/capture-arm /work/bandpass/capture-restart.s16 96000 513 48000 1 0
cmp /work/bandpass/capture-17.s16 /work/bandpass/capture-restart.s16
# Expected errors: coefficients and output format are deliberately fixed.
run /work/bandpass/capture-arm /dev/null 1 1 44100 1 1
run /work/bandpass/capture-arm /dev/null 1 1 48000 2 1
echo 'PASS: packaged plugin, actual ALSA route, read-size independence, same-handle prepare/reset, unsupported format rejection'
