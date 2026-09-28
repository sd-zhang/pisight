#!/bin/sh
# Delegate to the pinned firmware tree; product identity is already patched there.
set -eu
PISIGHT_SOURCE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PISIGHT_SOURCE_ROOT/webcampi"
exec ./build.sh
