#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "voice-filter.h"
#ifdef BASELINE
struct audio_config { int gain; unsigned hp, lp, bypass; };
static void voice_filter_update(struct voice_filter *f, struct audio_config c) { (void)f; (void)c; }
#endif
static double response(struct audio_config c, double hz)
{
 struct voice_filter f; voice_filter_reset(&f); voice_filter_update(&f,c);
 double in=0,out=0;
 for(int i=0;i<96000;i++) {
  float x=(float)(3000*sin(6.283185307179586*hz*i/48000));
  int y=voice_filter_sample(&f,x);
  if(i>=48000) {in+=(double)x*x;out+=(double)y*y;}
 }
 return 10*log10(out/in);
}
int main(void)
{
 struct audio_config c={60,0,0,0};
 double db=response(c,1000); printf("Gain +6 dB: %.4f\n",db);
 if(fabs(db-6)>.05) return 1;
 c=(struct audio_config){-120,0,0,0}; assert(fabs(response(c,1000)+12)<.05);
 c=(struct audio_config){0,80,8000,1}; assert(fabs(response(c,20))<.05);
 c=(struct audio_config){0,200,16000,0}; assert(fabs(response(c,200)+3.0103)<.1);
 assert(fabs(response(c,16000)+3.0103)<.1);
 c=(struct audio_config){0,0,0,0}; assert(fabs(response(c,20))<.05);
#ifndef BASELINE
 struct voice_filter f; voice_filter_reset(&f);
 c=(struct audio_config){-120,0,0,0}; voice_filter_update(&f,c);
 for(int i=0;i<960;i++) (void)voice_filter_sample(&f,1000);
 assert(f.remaining==0 && abs(voice_filter_sample(&f,1000)-251)<=1);
 c=(struct audio_config){240,0,0,0}; voice_filter_update(&f,c);
 int previous=251;
 for(int i=0;i<960;i++) {int y=voice_filter_sample(&f,1000);assert(abs(y-previous)<25);previous=y;}
 assert(voice_filter_sample(&f,10000)==32767 && f.clipped);
 c.bypass=1; voice_filter_update(&f,c);
 for(int i=0;i<960;i++) (void)voice_filter_sample(&f,0);
 assert(voice_filter_sample(&f,-0.5f)==-1);
 assert(voice_filter_sample(&f,32767.75f)==32767 && !f.clipped);
 c=(struct audio_config){0,20,1000,0}; voice_filter_update(&f,c);
 for(int i=0;i<960;i++) (void)voice_filter_sample(&f,0);
 (void)voice_filter_sample(&f,32767);
 for(int i=0;i<960000;i++) {(void)voice_filter_sample(&f,0);if(i%128==0)voice_filter_quiet_tail(&f);}
 assert(voice_filter_sample(&f,0)==0);
#endif
 puts("PASS: gain/cutoffs/bypass, smoothing, saturation and quiet tail");
 return 0;
}
