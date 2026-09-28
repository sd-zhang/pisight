#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "pisight-diagnostic.h"
static void command(uint8_t *p,int op,int source,uint32_t gen,uint32_t offset){memset(p,0,60);p[0]=1;p[1]=op;p[2]=source;pisight_diag_put32(p+4,gen);pisight_diag_put32(p+8,offset);}
int main(int argc,char **argv){
 assert(argc==3);const char *paths[]={argv[1],argv[2]};
 struct pisight_diagnostic d={0};uint8_t cmd[60],out[60],again[60];
 pisight_diag_read(&d,out);assert(out[1]==1);
 command(cmd,1,0,0,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);
 assert(out[1]==0&&out[2]==44&&pisight_diag_u32(out+8)==125);
 uint32_t generation=pisight_diag_u32(out+4);assert(generation);
 for(int i=0;i<44;i++)assert(out[16+i]==i);
 pisight_diag_read(&d,again);assert(!memcmp(out,again,60));
 // Growth of the source file cannot change an already selected snapshot.
 FILE *f=fopen(argv[1],"ab");assert(f);fputs("appended",f);fclose(f);
 command(cmd,2,0,generation,96);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);
 assert(out[1]==0&&out[2]==29&&out[3]==1&&pisight_diag_u32(out+8)==125);
 for(int i=0;i<29;i++)assert(out[16+i]==96+i);
 for(int i=45;i<60;i++)assert(out[i]==0);
 command(cmd,2,0,generation,125);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==0&&out[2]==0&&out[3]==1);
 command(cmd,2,0,generation,126);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==3&&out[2]==0);
 command(cmd,2,0,generation+1,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==4);
 command(cmd,1,0,0,0);cmd[59]=1;pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==4);
 command(cmd,1,2,0,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==4);
 command(cmd,1,0,0,0);pisight_diag_command(&d,cmd,59,paths);pisight_diag_read(&d,out);assert(out[1]==4);
 command(cmd,1,0,0,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==0&&pisight_diag_u32(out+8)==133&&pisight_diag_u32(out+4)!=generation);
 command(cmd,1,1,0,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==2&&out[2]==0);
 f=fopen(argv[2],"wb");assert(f);fclose(f);
 command(cmd,1,1,0,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==0&&out[2]==0&&out[3]==1);
 f=fopen(argv[2],"wb");assert(f);assert(!fseek(f,PISIGHT_DIAG_MAX,SEEK_SET));fputc(1,f);fclose(f);
 command(cmd,1,1,0,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==5&&out[2]==0);
 command(cmd,3,0,0,0);pisight_diag_command(&d,cmd,60,paths);pisight_diag_read(&d,out);assert(out[1]==1&&!d.data);
 pisight_diag_close(&d);puts("PASS: binary pages, retry stability, append isolation, EOF, range/generation/malformed requests, missing/empty/oversized files, release");
}
