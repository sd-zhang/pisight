#!/usr/bin/env python3
"""Exercise the built pigpio clock code with simulated peripheral registers.

This checks register ownership and the real I2S driver's early-return guard.
It does not simulate audio DMA, USB, or physical Pi behavior.
Usage: check-pcm-clock.py BUILDROOT_OUTPUT_BUILD [default|pwm]
"""
import pathlib
import re
import subprocess
import sys
import tempfile

build = pathlib.Path(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "default"
assert mode in ("default", "pwm")
pig = next(build.glob("pigpio-*/pigpio.c")).read_text()
header = next(build.glob("pigpio-*/pigpio.h")).read_text()
i2s = next(build.glob("linux-*/sound/soc/bcm/bcm2835-i2s.c")).read_text()


def function(name):
    start = re.search(r"static void " + name + r"\s*\([^;{]*\)\s*\{", pig).start()
    brace = pig.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (pig[end] == "{") - (pig[end] == "}")
        end += 1
    return pig[start:end]


defines = []
for source in (pig, header, i2s):
    for line in source.splitlines():
        if re.match(
            r"#define\s+(?:PCM_|PWM_|CLK_|BCM_PASSWD|PI_CLOCK_|"
            r"PI_WF_MICROS|PI_DEFAULT_CLK_|BCM2835_I2S_TXON|BCM2835_I2S_RXON)",
            line,
        ):
            assert not line.endswith("\\"), line
            defines.append(line)

guard = re.search(
    r"if \(csreg & \(BCM2835_I2S_TXON \| BCM2835_I2S_RXON\)\)\s*return 0;",
    i2s,
).group()

code = """
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#define DBG(...) ((void)0)
#define BIT(n) (1U << (n))
static void myGpioDelay(unsigned delay) { (void)delay; }
static uint32_t pcmReg[64], pwmReg[64], clkReg[64];
static struct { unsigned clockMicros, clockPeriph; } gpioCfg;
static unsigned clk_plld_freq = 500000000;
static struct dma_page { uint32_t periphData; } dma_page;
static struct dma_page *dmaIVirt[] = { &dma_page };
""" + "\n".join(defines)
code += "\n" + "\n".join(function(n) for n in ("initPWM", "initPCM", "initHWClk", "initClock"))
code += "\nstatic int i2s_will_configure(uint32_t csreg) {\n" + guard + "\nreturn 1;\n}\n"
clock = "PI_DEFAULT_CLK_PERIPHERAL" if mode == "default" else "PI_CLOCK_PWM"
code += """
int main(void) {
    gpioCfg.clockMicros = PI_DEFAULT_CLK_MICROS;
    gpioCfg.clockPeriph = CLOCK_SELECTION;
    initClock(1);
    unsigned pcm_changed = 0;
    for (unsigned i = 0; i < 64; ++i) pcm_changed |= pcmReg[i];
    int setup = i2s_will_configure(pcmReg[PCM_CS]);
    printf("pigpio clock=%s; PCM_CS=0x%08x PCM_RXC=0x%08x PCM_MODE=0x%08x\\n",
           gpioCfg.clockPeriph == PI_CLOCK_PCM ? "PCM" : "PWM",
           pcmReg[PCM_CS], pcmReg[PCM_RXC], pcmReg[PCM_MODE]);
    printf("I2S hw_params guard: %s\\n", setup ? "continues setup" : "SKIPS microphone setup");
    int conflict = pcm_changed || clkReg[CLK_PCMCTL] || clkReg[CLK_PCMDIV] || !setup;
    puts(conflict ? "FAIL: GPIO startup claims microphone peripheral" : "PASS: GPIO startup leaves PCM registers and clock untouched");
    return conflict ? 1 : 0;
}
""".replace("CLOCK_SELECTION", clock)

with tempfile.TemporaryDirectory(prefix="pisight-pcm-") as tmp:
    source = pathlib.Path(tmp) / "check.c"
    binary = pathlib.Path(tmp) / "check"
    source.write_text(code)
    subprocess.run(["cc", "-std=gnu11", "-O0", str(source), "-o", str(binary)], check=True)
    sys.exit(subprocess.run([str(binary)]).returncode)
