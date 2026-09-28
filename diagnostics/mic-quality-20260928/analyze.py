import wave,array,math,cmath,json,collections
from pathlib import Path
p=Path('diagnostics/capture-audio-sof-shutter-20260928/microphone.wav')
with wave.open(str(p)) as w:
 rate=w.getframerate();a=array.array('h',w.readframes(w.getnframes()))
def fft(x):
 n=len(x);j=0
 for i in range(1,n):
  bit=n>>1
  while j&bit:j^=bit;bit>>=1
  j^=bit
  if i<j:x[i],x[j]=x[j],x[i]
 length=2
 while length<=n:
  wm=cmath.exp(-2j*math.pi/length)
  for start in range(0,n,length):
   z=1
   for k in range(start,start+length//2):
    u=x[k];v=x[k+length//2]*z;x[k]=u+v;x[k+length//2]=u-v;z*=wm
  length*=2
 return x
nfft=8192;power=[0.]*(nfft//2+1);segments=0
for start in range(rate*5,len(a)-nfft,rate*2):
 x=fft([a[start+i]*(.5-.5*math.cos(2*math.pi*i/(nfft-1))) for i in range(nfft)])
 for k in range(len(power)):power[k]+=abs(x[k])**2
 segments+=1
peaks=[i for i in range(1,len(power)-1) if power[i]>power[i-1] and power[i]>power[i+1]]
total=sum(power)
bands={f'{lo}-{hi}Hz':100*sum(power[i] for i in range(len(power)) if lo<=i*rate/nfft<hi)/total for lo,hi in [(0,80),(80,300),(300,3400),(3400,8000),(8000,24001)]}
chunks=collections.Counter(bytes(a[i:i+480]) for i in range(rate,len(a)-480,480))
blocks=[]
for i in range(0,len(a),rate):
 b=a[i:i+rate];r=math.sqrt(sum(x*x for x in b)/len(b));blocks.append({'second':i/rate,'rms_dbfs':20*math.log10(max(r,1e-9)/32768),'peak':max(map(abs,b))})
rms=math.sqrt(sum(x*x for x in a)/len(a))
r={'input':str(p),'sample_rate':rate,'samples':len(a),'rms_dbfs':20*math.log10(rms/32768),'peak_dbfs':20*math.log10(max(map(abs,a))/32768),'clipped_samples':sum(abs(x)>=32767 for x in a),'mean_sample':sum(a)/len(a),'largest_sample_step':max(abs(y-x) for x,y in zip(a,a[1:])),'identical_10ms_blocks_extra_occurrences':sum(v-1 for v in chunks.values()),'spectral_segments':segments,'band_power_percent':bands,'strongest_local_spectral_peaks':[{'hz':i*rate/nfft,'fraction_power_percent':100*power[i]/total} for i in sorted(peaks,key=lambda i:power[i],reverse=True)[:12]],'one_second_levels':blocks,'limitations':['Ambient recording; no known speech or calibrated stimulus.','FFmpeg recording omits samples relative to PTS; cannot use it to establish uninterrupted transport.','Spectral power does not identify whether a sound is environmental, acoustic, or electronic.']}
out=Path('diagnostics/mic-quality-20260928/recording-analysis.json');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='one_second_levels'},indent=2))
