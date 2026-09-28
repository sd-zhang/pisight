#!/bin/sh
# Run in the existing Linux amd64 Buildroot environment, with volume at /work.
set -e
cd /work
tests=/work/diagnostics/audio-controls-tests
out=/work/audio-controls
cc=/work/buildroot/output/host/bin/arm-linux-gcc
mkdir -p "$out"
for test in dsp control areas live; do
    "$cc" -std=c11 -D_POSIX_C_SOURCE=200809L -DPIC -O2 -Wall -Wextra -Werror \
        -I/work/package/pisight-mic '-DCONFIG_STORE_PATH="/work/audio-controls/store-fixture"' \
        "$tests/$test.c" -lasound -lm -o "$out/$test-arm"
done
"$cc" -std=c11 -D_POSIX_C_SOURCE=200809L -O2 -I/work/package/pisight-mic \
    /work/diagnostics/bandpass-tests/filter-test.c -lm -o "$out/default-filter-arm"
cat > "$out/store-fixture" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> /work/audio-controls/store-calls
sleep 0.05
exit "${TEST_STORE_FAIL:-0}"
EOF
chmod +x "$out/store-fixture"
