#define _POSIX_C_SOURCE 200809L
#include "pisight-controls.h"
#include <assert.h>
#ifndef STORE_CALLS_PATH
#define STORE_CALLS_PATH "/tmp/pisight-video-store-calls"
#endif
static void command(uint8_t *p,unsigned op,unsigned modes,unsigned token)
{memset(p,0,32);p[0]=1;p[1]=op;audio_put32(p+4,token);if(op==1)p[8]=modes;}
static void wait_save(struct pisight_controls *s)
{for(int i=0;i<100 && s->writer;i++){struct timespec t={0,10000000};nanosleep(&t,0);pisight_controls_poll(s);}assert(!s->writer);}
int main(void)
{
 unlink(AUDIO_RUNTIME_PATH);unsetenv("ISIGHT_RESOLUTIONS");
 struct pisight_controls s;pisight_controls_init(&s);uint8_t p[32],r[32];
 pisight_controls_read(&s,2,r);
 if(r[1]!=0 || r[8]!=7) {puts("FAIL: video selector must report the three default advertised modes");return 1;}
 assert(r[16]==7 && r[24]==7 && !r[2]);
 for(unsigned modes=1;modes<=7;modes++) {
  command(p,1,modes,modes);pisight_controls_command(&s,2,p,32);pisight_controls_read(&s,2,r);
  assert(r[1]==0 && r[8]==modes && r[16]==7 && r[24]==7 && r[2]==(modes==7?0:2));
 }
 command(p,1,1,8);pisight_controls_command(&s,2,p,32);
 for(unsigned bad=0;bad<=255;bad++)if(bad==0 || bad>7) {
  command(p,1,bad,9);pisight_controls_command(&s,2,p,32);pisight_controls_read(&s,2,r);
  assert(r[1]==1 && r[8]==1);
 }
 for(unsigned reserved=9;reserved<32;reserved++) {
  command(p,1,2,10);p[reserved]=1;pisight_controls_command(&s,2,p,32);pisight_controls_read(&s,2,r);assert(r[1]==1 && r[8]==1);
 }
 command(p,2,0,11);pisight_controls_command(&s,2,p,32);assert(s.writer);
 command(p,3,0,12);pisight_controls_command(&s,2,p,32);pisight_controls_read(&s,2,r);assert(audio_u32(r+4)==11 && r[1]==3 && r[2]&4);
 wait_save(&s);pisight_controls_read(&s,2,r);assert(r[1]==0 && r[2]==8 && r[16]==1 && r[24]==7);
 command(p,3,0,13);pisight_controls_command(&s,2,p,32);pisight_controls_read(&s,2,r);assert(r[8]==7 && r[2]==10);
 setenv("TEST_STORE_FAIL","1",1);command(p,2,0,14);pisight_controls_command(&s,2,p,32);wait_save(&s);pisight_controls_read(&s,2,r);
 assert(r[1]==2 && r[16]==1 && r[2]==10);unsetenv("TEST_STORE_FAIL");
 command(p,2,0,15);pisight_controls_command(&s,2,p,32);wait_save(&s);pisight_controls_read(&s,2,r);assert(r[1]==0 && !r[2]);
 pisight_controls_close(&s);setenv("ISIGHT_RESOLUTIONS","1920x1080 ",1);pisight_controls_init(&s);pisight_controls_read(&s,2,r);
 assert(r[8]==2 && r[16]==2 && r[24]==2 && !r[2]);pisight_controls_close(&s);
 /* Older custom lists remain untouched until an explicit preset selection. */
 setenv("ISIGHT_RESOLUTIONS","640x480 1280x720 ",1);pisight_controls_init(&s);pisight_controls_read(&s,2,r);
 assert(r[8]==0 && r[16]==0 && r[24]==0 && !r[2]);
 command(p,2,0,16);pisight_controls_command(&s,2,p,32);pisight_controls_read(&s,2,r);assert(!s.writer && r[1]==1);pisight_controls_close(&s);
 /* Save canonicalizes ordering, so a reordered existing set needs a restart. */
 setenv("ISIGHT_RESOLUTIONS","1920x1080 1280x720 ",1);pisight_controls_init(&s);pisight_controls_read(&s,2,r);assert(r[8]==3 && !r[2]);
 command(p,2,0,17);pisight_controls_command(&s,2,p,32);wait_save(&s);pisight_controls_read(&s,2,r);assert(r[1]==0 && r[2]==8);
 /* Explicit software apply uses a distinct save+reboot helper operation. */
 command(p,1,1,18);pisight_controls_command(&s,2,p,32);
 command(p,4,0,19);pisight_controls_command(&s,2,p,32);assert(s.writer);
 wait_save(&s);pisight_controls_read(&s,2,r);assert(r[1]==0 && r[16]==1 && r[24]==3 && r[2]==8);
 FILE *calls=fopen(STORE_CALLS_PATH,"r");assert(calls);
 char line[128],last[128]={0};while(fgets(line,sizeof line,calls))strcpy(last,line);fclose(calls);
 assert(!strcmp(last,"--resolutions-reboot 1\n"));
 /* Reboot is exclusive to video selector and malformed packets cannot invoke it. */
 command(p,4,0,20);p[8]=1;pisight_controls_command(&s,2,p,32);pisight_controls_read(&s,2,r);assert(!s.writer && r[1]==1);
 command(p,4,0,21);pisight_controls_command(&s,1,p,32);pisight_controls_read(&s,1,r);assert(!s.writer && r[1]==1);
 pisight_controls_close(&s);unlink(AUDIO_RUNTIME_PATH);
 puts("PASS: all seven mode sets, invalid masks/padding, desired/saved/active readback, async save/error/busy, boot reload and custom lists");
}
