/* Native test for the real diagnostic predicate. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
typedef uint64_t u64;
#define current get_current() /* Linux reserves this macro name. */
#include "isoc-diag.h"
int main(void)
{
    unsigned cases = 0;
    for (u32 field=0; field<4; ++field) {
        u64 cutoff=90000+6250*field;
        for (u32 frame=0; frame<16384; ++frame) {
            u32 next=(frame+1)&16383;
            assert(dwc2_diag_before_eopf(true,frame,1000000,next,1000000+cutoff-1,field<<11));
            assert(!dwc2_diag_before_eopf(true,frame,1000000,next,1000000+cutoff,field<<11));
            assert(!dwc2_diag_before_eopf(false,frame,1000000,next,1000001,field<<11));
            assert(!dwc2_diag_before_eopf(true,frame,1000000,frame,1000001,field<<11));
            assert(!dwc2_diag_before_eopf(true,frame,1000000,(frame+2)&16383,1000001,field<<11));
            assert(!dwc2_diag_before_eopf(true,frame,1000000,next,999999,field<<11));
            assert(!dwc2_diag_before_eopf(true,frame,1000000,next,2049000001ULL,field<<11));
            cases+=7;
        }
    }
    printf("%u predicate checks passed; no hardware timing claim.\n",cases);
}
