#define _POSIX_C_SOURCE 200809L
#include "pisight-controls.h"
#include <assert.h>
static void command(uint8_t *p,unsigned op,uint32_t token,struct audio_config c)
{memset(p,0,32);p[0]=1;p[1]=op;audio_put32(p+4,token);if(op==1)audio_encode(p+8,c);}
static void await_save(struct pisight_controls *s)
{for(int i=0;i<100 && s->writer;i++){struct timespec t={0,10000000};nanosleep(&t,0);pisight_controls_poll(s);}assert(!s->writer);}
int main(void)
{
 unlink(AUDIO_RUNTIME_PATH);unlink(DIAGNOSTICS_RUNTIME_PATH);
 unsetenv("ISIGHT_AUDIO");unsetenv("ISIGHT_DIAGNOSTICS");
 struct pisight_controls s;pisight_controls_init(&s);assert(s.shared);
 uint8_t p[32],r[32];struct audio_config c={60,120,12000,0};
 command(p,1,41,c);pisight_controls_command(&s,0,p,32);pisight_controls_read(&s,0,r);
 assert(r[1]==0 && (r[2]&2) && audio_u32(r+4)==41 && audio_pack(audio_decode(r+8))==audio_pack(c));
 uint32_t before=audio_load(&s.shared->requested);
 for(int n=0;n<32;n++){pisight_controls_command(&s,0,p,n);assert(audio_load(&s.shared->requested)==before);}
 p[15]=1;pisight_controls_command(&s,0,p,32);assert(s.reply[0].status==1);p[15]=0;
 c.gain=61;command(p,1,42,c);pisight_controls_command(&s,0,p,32);assert(s.reply[0].status==1);
 assert(audio_load(&s.shared->requested)==before);
 command(p,2,43,c);pisight_controls_command(&s,0,p,32);assert(s.writer && s.reply[0].status==3);
 command(p,3,44,c);pisight_controls_command(&s,0,p,32);assert(s.reply[0].token==43 && audio_load(&s.shared->requested)==before);
 await_save(&s);assert(s.reply[0].status==0 && s.saved_audio==before);
 pisight_controls_read(&s,0,r);assert(!(r[2]&2));
 setenv("TEST_STORE_FAIL","1",1);command(p,2,45,c);pisight_controls_command(&s,0,p,32);await_save(&s);assert(s.reply[0].status==2);unsetenv("TEST_STORE_FAIL");
 command(p,1,46,audio_default());memset(p+8,0,8);p[8]=1;pisight_controls_command(&s,1,p,32);
 assert(audio_diagnostics_get()==1);pisight_controls_read(&s,1,r);assert(r[8]==1 && (r[2]&2));
 command(p,2,47,c);pisight_controls_command(&s,1,p,32);await_save(&s);assert(s.saved_diagnostics==1 && s.reply[1].status==0);
 command(p,3,48,c);pisight_controls_command(&s,1,p,32);assert(!audio_diagnostics_get());
 command(p,3,49,c);pisight_controls_command(&s,0,p,32);assert(audio_load(&s.shared->requested)==audio_pack(audio_default()));
 /* A whole preset must never tear when separate processes update it. */
 uint32_t a=audio_pack((struct audio_config){-240,20,1000,1});
 uint32_t b=audio_pack((struct audio_config){240,500,20000,0});
 audio_store(&s.shared->requested,a);pid_t child=fork();assert(child>=0);
 if(!child){for(int i=0;i<100000;i++)audio_store(&s.shared->requested,i&1?a:b);_exit(0);}
 for(int i=0;i<100000;i++){uint32_t v=audio_load(&s.shared->requested);assert(v==a || v==b);}
 int status;assert(waitpid(child,&status,0)==child && status==0);
 pisight_controls_close(&s);
 setenv("ISIGHT_AUDIO","-30 200 16000 1",1);setenv("ISIGHT_DIAGNOSTICS","1",1);
 pisight_controls_init(&s);assert(s.saved_audio==audio_pack((struct audio_config){-30,200,16000,1}) && s.saved_diagnostics==1);
 pisight_controls_close(&s);unlink(AUDIO_RUNTIME_PATH);unlink(DIAGNOSTICS_RUNTIME_PATH);
 puts("PASS: validated UVC payloads, RAM apply, async save/error, busy tokens, defaults, diagnostics and atomic IPC");
}
