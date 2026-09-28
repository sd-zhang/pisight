#!/bin/sh
# Run under pisight-emulation:arm64; root can be packaged extraction or target.
set -e
export QEMU_LD_PREFIX=${PISIGHT_TEST_ROOT:-/work/buildroot/output/target}
run() { qemu-arm-static -cpu arm1176 "$@"; }
for test in dsp control areas live default-filter; do run "/work/audio-controls/$test-arm"; done
export ALSA_PLUGIN_DIR=/work/bandpass/plugins
export ALSA_CONFIG_PATH=/work/bandpass/asound.conf
cp "$QEMU_LD_PREFIX/usr/lib/alsa-lib/libasound_module_pcm_pisight_voice.so" "$ALSA_PLUGIN_DIR/"
run /work/bandpass/capture-arm /work/audio-controls/capture-17.s16 96000 17 48000 1 0
run /work/bandpass/capture-arm /work/audio-controls/capture-1024.s16 96000 1024 48000 1 0
cmp /work/audio-controls/capture-17.s16 /work/audio-controls/capture-1024.s16
TEST_RESTART=1 run /work/bandpass/capture-arm /work/audio-controls/capture-restart.s16 96000 513 48000 1 0
cmp /work/audio-controls/capture-17.s16 /work/audio-controls/capture-restart.s16
run /work/bandpass/capture-arm /dev/null 1 1 44100 1 1
run /work/bandpass/capture-arm /dev/null 1 1 48000 2 1
echo 'PASS: actual ALSA plugin/route, split reads, same-handle prepare, incompatible formats'
