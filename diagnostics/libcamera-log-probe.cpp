#include <libcamera/base/log.h>
#include <libcamera/logging.h>
#include <chrono>
#include <cstdio>
#include <iomanip>
#include <sstream>
#include <cstring>
#include <stdexcept>

using namespace libcamera;
namespace libcamera { LOG_DEFINE_CATEGORY(PiSightLoggingProbe) }

static int formatted;
static int prefixed;
struct Value { double number; };
std::ostream &operator<<(std::ostream &out, const Value &value)
{
    ++formatted;
    return out << value.number;
}
class Context : public Loggable {
public:
    void debug() { LOG(PiSightLoggingProbe, Debug) << Value{1.2345}; }
    void info() { LOG(PiSightLoggingProbe, Info) << "visible " << Value{2.5}; }
    static void staticInfo() { using libcamera::_log; LOG(PiSightLoggingProbe, Info) << "static-visible"; }
private:
    std::string logPrefix() const override { ++prefixed; return "probe-prefix"; }
};
int main(int argc, char **argv)
{
    if (argc > 1 && !std::strcmp(argv[1], "--fatal")) {
        const_cast<LogCategory &>(logCategoryPiSightLoggingProbe()).setSeverity(static_cast<LogSeverity>(100));
        LOG(PiSightLoggingProbe, Fatal) << "must still abort above an extreme threshold";
        return 99;
    }
    if (argc > 1 && !std::strcmp(argv[1], "--assert")) {
        ASSERT(false);
        return 99;
    }
    ASSERT(true);
    std::ostringstream output;
    logSetStream(&output);
    logSetLevel("*", "INFO");
    Context context;
    auto start = std::chrono::steady_clock::now();
    for (int i = 0; i != 20000; ++i)
        LOG(PiSightLoggingProbe, Debug) << "At t " << Value{5000.0+i} << " r " << 0.91 << " b " << 0.53;
    auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    int suppressedFormatted = formatted;
    context.debug();
    int suppressedPrefixes = prefixed;
    LOG(Debug) << Value{3.0};
    int suppressedTotal = formatted;
    bool threw = false;
    try {
        LOG(PiSightLoggingProbe, Debug) << []() -> int { throw std::runtime_error("disabled operand evaluated"); }();
    } catch (const std::runtime_error &) { threw = true; }
    bool outsideElse = false;
    if (false)
        LOG(PiSightLoggingProbe, Debug) << Value{4.0};
    else
        outsideElse = true;
    bool discarded = output.str().empty();
    context.info();
    Context::staticInfo();
    libcamera::LOG(PiSightLoggingProbe, Warning) << "qualified " << std::hex << 42;
    bool enabled = output.str().find("visible 2.5") != std::string::npos &&
                   output.str().find("probe-prefix") != std::string::npos &&
                   output.str().find("qualified 2a") != std::string::npos &&
                   output.str().find("static-visible") != std::string::npos;
    logSetLevel("PiSightLoggingProbe", "DEBUG");
    LOG(PiSightLoggingProbe, Debug) << "debug-enabled";
    bool dynamic = output.str().find("debug-enabled") != std::string::npos;
    logSetLevel("PiSightLoggingProbe", "ERROR");
    int previousFormatted = formatted;
    LOG(PiSightLoggingProbe, Warning) << Value{9.0};
    bool disabledAgain = formatted == previousFormatted;
    std::printf("suppressed_messages=20000 formatter_calls=%d elapsed_seconds=%.6f\n", suppressedFormatted, elapsed);
    std::printf("suppressed_prefixes=%d suppressed_total=%d no_output=%d enabled_output=%d dynamic_enable=%d else_binding=%d\n",
                suppressedPrefixes, suppressedTotal, discarded, enabled, dynamic, outsideElse);
    std::printf("disabled_throw_skipped=%d dynamic_disable=%d\n", !threw, disabledAgain);
    return threw || !disabledAgain || suppressedFormatted || suppressedPrefixes || suppressedTotal || !discarded || !enabled || !dynamic || !outsideElse;
}
