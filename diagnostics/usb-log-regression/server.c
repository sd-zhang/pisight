#include "pisight-diagnostic.h"
int main(int argc,char **argv){
 if(argc!=3)return 2;
 const char *paths[]={argv[1],argv[2]};struct pisight_diagnostic state={0};uint8_t in[60],out[60];
 while(fread(in,1,60,stdin)==60){pisight_diag_command(&state,in,60,paths);pisight_diag_read(&state,out);if(fwrite(out,1,60,stdout)!=60)return 3;fflush(stdout);}
 pisight_diag_close(&state);return 0;
}
