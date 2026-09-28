#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32; typedef uint16_t u16;
#define DSTS_SOFFN_LIMIT 0x3fff
#define USB_SPEED_HIGH 3
struct dwc2_hsotg { struct { int speed; } gadget; u32 frame_number; };
struct dwc2_hsotg_ep {struct dwc2_hsotg *parent; u32 target_frame; unsigned interval; bool frame_overrun;};
static inline void dwc2_gadget_incr_frame_num(struct dwc2_hsotg_ep *hs_ep)
{
	struct dwc2_hsotg *hsotg = hs_ep->parent;
	u16 limit = DSTS_SOFFN_LIMIT;

	if (hsotg->gadget.speed != USB_SPEED_HIGH)
		limit >>= 3;

	hs_ep->target_frame += hs_ep->interval;
	if (hs_ep->target_frame > limit) {
		hs_ep->frame_overrun = true;
		hs_ep->target_frame &= limit;
	} else {
		hs_ep->frame_overrun = false;
	}
}
static bool dwc2_gadget_target_frame_elapsed(struct dwc2_hsotg_ep *hs_ep)
{
	struct dwc2_hsotg *hsotg = hs_ep->parent;
	u32 target_frame = hs_ep->target_frame;
	u32 current_frame = hsotg->frame_number;
	bool frame_overrun = hs_ep->frame_overrun;
	u16 limit = DSTS_SOFFN_LIMIT;

	if (hsotg->gadget.speed != USB_SPEED_HIGH)
		limit >>= 3;

	if (!frame_overrun && current_frame >= target_frame)
		return true;

	if (frame_overrun && current_frame >= target_frame &&
	    ((current_frame - target_frame) < limit / 2))
		return true;

	return false;
}
int main(void){
 for(unsigned interval=1; interval<=8; interval*=2){
  struct dwc2_hsotg hs={.gadget.speed=USB_SPEED_HIGH,.frame_number=0x3ff9};
  struct dwc2_hsotg_ep ep={.parent=&hs,.target_frame=0,.interval=interval,.frame_overrun=true};
  printf("interval=%u before increment: target=%u overrun=%u elapsed=%u\n",interval,ep.target_frame,ep.frame_overrun,dwc2_gadget_target_frame_elapsed(&ep));
  dwc2_gadget_incr_frame_num(&ep);
  printf("interval=%u after increment: target=%u overrun=%u elapsed=%u\n",interval,ep.target_frame,ep.frame_overrun,dwc2_gadget_target_frame_elapsed(&ep));
 }
}
