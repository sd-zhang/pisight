/* Actual plugin callback: atomic requests, fade acknowledgement and meters. */
#include "pcm_pisight_voice.c"
#include <assert.h>
#include <stdio.h>
int main(void)
{
 unlink(AUDIO_RUNTIME_PATH);
 struct voice_pcm v={0};v.ext.private_data=&v;v.ext.rate=48000;
 v.shared=audio_map(AUDIO_RUNTIME_PATH);assert(v.shared);
 assert(voice_init(&v.ext)==0);
 int32_t in[4800];int16_t out[4800];
 for(unsigned i=0;i<4800;i++)in[i]=10000*65536;
 snd_pcm_channel_area_t src={in,0,32},dst={out,0,16};
 uint32_t a=audio_pack((struct audio_config){60,0,0,0});
 uint32_t b=audio_pack((struct audio_config){-60,0,0,0});
 audio_store(&v.shared->requested,a);
 assert(voice_transfer(&v.ext,&dst,0,&src,0,480)==480);
 assert(audio_load(&v.shared->applied)==audio_pack(audio_default()));
 audio_store(&v.shared->requested,b);
 assert(voice_transfer(&v.ext,&dst,0,&src,0,480)==480);
 assert(audio_load(&v.shared->applied)==a);
 assert(voice_transfer(&v.ext,&dst,0,&src,0,960)==960);
 assert(audio_load(&v.shared->applied)==b && abs(out[959]-5012)<=1);
 audio_store(&v.shared->requested,audio_pack((struct audio_config){240,0,0,0}));
 assert(voice_transfer(&v.ext,&dst,0,&src,0,4800)==4800);
 assert(out[4799]==32767 && audio_load(&v.shared->clips)>0);
 assert(audio_load(&v.shared->peak)==32767 && audio_load(&v.shared->heartbeat)>0);
 audio_store(&v.shared->requested,audio_pack((struct audio_config){240,500,1000,1}));
 assert(voice_init(&v.ext)==0);
 assert(!audio_load(&v.shared->heartbeat) && !audio_load(&v.shared->clips));
 /* Low bits near S16 boundaries must not be rounded by the float conversion. */
 const int32_t edge[]={INT32_MAX,INT32_MIN,-1,-65537,65535,65536,2147418111};
 for(unsigned i=0;i<sizeof edge/sizeof *edge;i++)in[i]=edge[i];
 assert(voice_transfer(&v.ext,&dst,0,&src,0,7)==7);
 for(unsigned i=0;i<7;i++)assert(out[i]==(int16_t)((uint32_t)in[i]>>16));
 assert(!v.clips);
 munmap(v.shared,sizeof(*v.shared));unlink(AUDIO_RUNTIME_PATH);
 puts("PASS: live mid-fade requests, applied acknowledgement, meters, reset and bit-exact S32 bypass");
}
