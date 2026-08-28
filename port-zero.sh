#!/usr/bin/env bash
set -euo pipefail

cd ~/git/pisight/webcampi

echo "Creating Raspberry Pi Zero 1.3 board target..."

rm -rf board/raspberrypizero
cp -R board/raspberrypizero2w-64 board/raspberrypizero

cp configs/webcampi_raspberrypizero2w_64_defconfig \
   configs/webcampi_raspberrypizero_defconfig

python3 <<'PY'
from pathlib import Path

p = Path("configs/webcampi_raspberrypizero_defconfig")
s = p.read_text()

s = s.replace(
"""BR2_aarch64=y
BR2_ARM_FPU_VFPV4=y
BR2_TOOLCHAIN_EXTERNAL=y
BR2_TOOLCHAIN_EXTERNAL_BOOTLIN=y
BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE=y""",
"""BR2_arm=y
BR2_arm1176jzf_s=y
BR2_TOOLCHAIN_EXTERNAL=y
BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_ARMV6_EABIHF_GLIBC_STABLE=y"""
)

s = s.replace(
    "board/raspberrypizero2w-64/",
    "board/raspberrypizero/"
)

s = s.replace(
    'BR2_LINUX_KERNEL_DEFCONFIG="bcm2711"',
    'BR2_LINUX_KERNEL_DEFCONFIG="bcmrpi"'
)

s = s.replace(
    'BR2_LINUX_KERNEL_INTREE_DTS_NAME="broadcom/bcm2710-rpi-zero-2-w"',
    'BR2_LINUX_KERNEL_INTREE_DTS_NAME="broadcom/bcm2708-rpi-zero"'
)

p.write_text(s)
PY

cat > build.sh <<'EOF'
#!/bin/sh

BR2_EXTERNAL="$(pwd)" make -C buildroot/ webcampi_raspberrypizero_defconfig

KBUILD_BUILD_USER=webcampi \
KBUILD_BUILD_HOST=webcampi \
make -C buildroot/ all
EOF

chmod +x build.sh

echo
echo "=== New target ==="
grep -E \
'BR2_(arm|arm1176|TOOLCHAIN_EXTERNAL|LINUX_KERNEL_DEFCONFIG|LINUX_KERNEL_INTREE_DTS_NAME|PACKAGE_LIBCAMERA|PACKAGE_UVC_GADGET)|raspberrypizero/' \
configs/webcampi_raspberrypizero_defconfig || true

echo
echo "Done."
echo "Build with:"
echo "  cd ~/git/pisight"
echo "  ./build.sh"
