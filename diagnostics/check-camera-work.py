#!/usr/bin/env python3
"""Compile real production methods to check output equivalence and avoided work.

Detects cache invalidation/arithmetic changes and lost/repeated camera controls.
Fake camera only replaces the hardware queue boundary; real routing/setters run.
Use --emit to retain the portable C++ harness for ARM compilation/benchmarks.
"""
import argparse,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('source',type=pathlib.Path);p.add_argument('--emit',type=pathlib.Path);p.add_argument('--benchmark',action='store_true');p.add_argument('--lens-only',action='store_true');a=p.parse_args()
def block(text,marker):
 start=text.index(marker);opening=text.index('{',start);i=opening+1;depth=1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
vc=(a.source/'src/ipa/rpi/vc4/vc4.cpp').read_text();cam=(a.source/'lib/libcamera-source.cpp').read_text()
ref=(pathlib.Path(__file__).resolve().parent/'fixtures/vc4-resample-reference.cpp').read_text()
cache=block(vc,'struct LsSampling')+';\n' if 'struct LsSampling' in vc else ''
# Extract the optional member along with its aggregate declaration.
if cache:
 end=vc.index('}',vc.index('struct LsSampling'))
 cache=vc[vc.index('struct LsSampling'):vc.index(';',end)+1]+'\n'
method=block(vc,'void IpaVc4::resampleTable')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <chrono>
#include <memory>
#include <vector>
#include <map>
#include <atomic>
#include <mutex>
#include <queue>
#include <functional>
#include <unistd.h>
#include <fcntl.h>
#include <cerrno>
#include <iostream>
static unsigned long long floors;
static double countedFloor(double x) {
#ifndef PISIGHT_BENCHMARK
 ++floors;
#endif
 return std::floor(x);
}
'''+ref+r'''
#define floor countedFloor
class IpaVc4 { public:
'''+cache+r'''
 void resampleTable(uint16_t[], const std::vector<double>&, int, int);
};
'''+method+r'''
#undef floor
static void lensTests(bool bench) {
 IpaVc4 c; std::vector<double> src(192,1.0); uint16_t out[64*49], want[64*49];
 c.resampleTable(out,src,42,25); auto before=floors;
 c.resampleTable(out,src,42,25);
 bool reused=floors-before==42*25;
 unsigned long long checked=0; uint32_t seed=123;
 for(int w=2;w<=64;w++) for(int h=2;h<=49;h++) {
  for(int trial=0;trial<3;trial++) {
   for(auto &x:src) { seed=seed*1664525u+1013904223u; x=(seed%32769)/1024.0; }
   if(trial==0) std::fill(src.begin(),src.end(),1.0);
   c.resampleTable(out,src,w,h); reference(want,src,w,h);
   for(int i=0;i<w*h;i++) { if(trial==0) assert(out[i]==1024); if(out[i]!=want[i]) { std::cerr<<"grid mismatch "<<w<<","<<h<<" at "<<i<<"\n"; std::exit(1); } ++checked; }
  }
 }
 // Revisit prior dimensions and values; same geometry must not freeze gains.
 for(int i=0;i<50;i++) {
  int w=i%2?64:42,h=i%3?49:25;
  std::fill(src.begin(),src.end(),i%2?1.00048828125:15.99951171875);
  c.resampleTable(out,src,w,h);reference(want,src,w,h);
  assert(std::equal(out,out+w*h,want));
 }
 std::fill(src.begin(),src.end(),32.0);c.resampleTable(out,src,64,49);
 for(int i=0;i<64*49;i++)assert(out[i]==16383);
 std::cout<<"lens_equivalent_values="<<checked<<" reused_geometry="<<(bench?"uninstrumented":(reused?"yes":"no"))<<"\n";
 if(!bench && !reused) { std::cerr<<"FAIL: unchanged grid repeats geometry calculations\n"; std::exit(1); }
 if(bench) {
  const int n=10000; volatile uint64_t sum=0;
  auto t=std::chrono::steady_clock::now();
  for(int j=0;j<n;j++) { src[j%192]=1.0+(j%100)/100.0;reference(want,src,42,25);sum+=want[j%1050]; }
  auto u=std::chrono::steady_clock::now();
  for(int j=0;j<n;j++) { src[j%192]=1.0+(j%100)/100.0;c.resampleTable(out,src,42,25);sum+=out[j%1050]; }
  auto v=std::chrono::steady_clock::now();
  std::cout<<"reference_us="<<std::chrono::duration<double,std::micro>(u-t).count()/n<<" candidate_us="<<std::chrono::duration<double,std::micro>(v-u).count()/n<<" checksum="<<sum<<"\n";
 }
}
struct Rectangle { int x=0,y=0; unsigned width=0,height=0; Rectangle()=default;Rectangle(int a,int b,unsigned c,unsigned d):x(a),y(b),width(c),height(d){} };
namespace controls { static int ScalerCrop,ExposureValue; }
struct Value { Rectangle crop;float ev=0; };
struct ControlList {
 std::map<const int*,Value> v;
 void set(const int&k,Rectangle r) {v[&k].crop=r;}
 void set(const int&k,float e) {v[&k].ev=e;}
};
struct Stream {};struct FrameBuffer {};
struct Request {
 enum {ReuseBuffers, RequestPending, RequestCancelled};int state=RequestPending;unsigned id;ControlList ctl;Request(unsigned i):id(i){}
 int status(){return state;}int addBuffer(Stream*,FrameBuffer*){return 0;}
 unsigned cookie(){return id;}void reuse(int){ctl.v.clear();state=RequestPending;}ControlList& controls(){return ctl;}
};
struct Camera {
 std::map<const int*,int> supported{{&controls::ScalerCrop,1},{&controls::ExposureValue,1}};
 std::vector<ControlList> queued;int fail=0;std::function<void(Request*)> onQueue;ControlList started;
 std::unique_ptr<Request> createRequest(unsigned i){return std::make_unique<Request>(i);}
 int start(ControlList*c){started=*c;return 0;}int stop(){return 0;}
 auto &controls(){return supported;}
 int queueRequest(Request*r){if(fail){int x=fail;fail=0;return x;}queued.push_back(r->ctl);if(onQueue)onQueue(r);return 0;}
};
struct ConfigEntry {Stream st;Stream *stream(){return &st;}};
struct Config {ConfigEntry e;ConfigEntry& at(int){return e;}};
struct Allocator {std::vector<std::unique_ptr<FrameBuffer>> data;Allocator(){for(int i=0;i<4;i++)data.emplace_back(new FrameBuffer);}
 auto& buffers(Stream*){return data;}};
struct MjpegEncoder {};
struct video_source {void *events=nullptr;int type=0;};
static constexpr int EVENT_READ=1, VIDEO_SOURCE_DMABUF=2;
static void events_watch_fd(void*,int,int,void(*)(void*),void*){}
static void events_unwatch_fd(void*,int,int){}
static void libcamera_source_video_process(void*){}

struct video_buffer {unsigned index;};
enum video_source_control { VIDEO_SOURCE_CTRL_ZOOM, VIDEO_SOURCE_CTRL_EV, BAD_CONTROL };
struct libcamera_source {
 video_source src;std::shared_ptr<Camera> camera=std::make_shared<Camera>();
 Rectangle default_crop{0,0,1920,1080};unsigned zoom=100;int ev_tenths=0;
 ControlList controls;std::atomic<bool> stopping{false};std::atomic<bool> controls_pending{true};
 std::unique_ptr<Config> config=std::make_unique<Config>();Allocator storage;Allocator *allocator=&storage;
 bool pipe_error_logged=false;uint64_t encoded_frames=0,dropped_frames=0;int pfds[2];MjpegEncoder *encoder=nullptr;
 std::mutex completion_mutex;std::queue<Request*> completed_requests;std::queue<video_buffer> encoded_buffers;
 void notifyCompletion(){}void pipeError(const char*,int){}void requestComplete(Request*);
 libcamera_source(){assert(pipe(pfds)==0);fcntl(pfds[0],F_SETFL,O_NONBLOCK);}
 ~libcamera_source(){close(pfds[0]);close(pfds[1]);}

 std::vector<std::unique_ptr<Request>> requests;
};
#define to_libcamera_source(s) reinterpret_cast<libcamera_source*>(s)
'''
for m in ['static void libcamera_source_apply_controls','static int libcamera_source_set_control']:
 code+=block(cam,m)+'\n'
if 'static int libcamera_source_queue_request' in cam:
 code+=block(cam,'static int libcamera_source_queue_request')+'\n'
# Skip the forward declaration by finding the actual definition.
marker='static int libcamera_source_queue_buffer'
start=cam.rindex(marker);code+=block(cam[start:],marker)+'\n'
for marker in ['void libcamera_source::requestComplete', 'static int libcamera_source_stream_on', 'static int libcamera_source_stream_off']:
 code+=block(cam,marker)+'\n'
code+=r'''
static void controlTests(bool bench) {
 libcamera_source s;for(unsigned i=0;i<4;i++)s.requests.emplace_back(new Request(i));
 video_buffer b{0}; assert(libcamera_source_queue_buffer(&s.src,&b)==0);
 assert(s.camera->queued.back().v.size()==2);
 for(int i=0;i<100;i++){b.index=i%4;assert(libcamera_source_queue_buffer(&s.src,&b)==0);}
 unsigned repeats=0;for(size_t i=1;i<s.camera->queued.size();i++)repeats+=!s.camera->queued[i].v.empty();
 std::cout<<"unchanged_requests_with_controls="<<repeats<<"\n";
 if(!bench && repeats) {std::cerr<<"FAIL: unchanged settings retransmitted every request\n";std::exit(1);}
 assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_ZOOM,200)==0);
 assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_EV,7)==0);
 assert(libcamera_source_queue_buffer(&s.src,&b)==0);
 auto c=s.camera->queued.back();assert(c.v[&controls::ScalerCrop].crop.width==960);assert(c.v[&controls::ScalerCrop].crop.x==480);assert(c.v[&controls::ExposureValue].ev==0.7f);
 assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_ZOOM,200)==0);
 assert(libcamera_source_queue_buffer(&s.src,&b)==0);
 if(!bench) assert(s.camera->queued.back().v.empty());
 assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_ZOOM,99)==-ERANGE);
 assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_EV,21)==-ERANGE);
 assert(libcamera_source_set_control(&s.src,BAD_CONTROL,1)==-EINVAL);
 if(!bench) {
  // Hardware queue rejection must not consume a pending update.
  assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_EV,-10)==0);
  s.camera->fail=-EIO;assert(libcamera_source_queue_buffer(&s.src,&b)==-EIO);
  assert(libcamera_source_queue_buffer(&s.src,&b)==0);assert(s.camera->queued.back().v[&controls::ExposureValue].ev==-1.0f);
  // No camera access after stopping; latest stopped-state change remains pending.
  s.stopping=true;auto n=s.camera->queued.size();
  assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_ZOOM,350)==0);
  assert(libcamera_source_queue_buffer(&s.src,&b)==0);assert(s.camera->queued.size()==n);
  s.stopping=false;assert(libcamera_source_queue_buffer(&s.src,&b)==0);assert(s.camera->queued.back().v[&controls::ScalerCrop].crop.width==548);
  // Accepted then cancelled asynchronously: use a distinct surviving request.
  assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_EV,3)==0);
  assert(libcamera_source_queue_buffer(&s.src,&b)==0);
  s.requests[b.index]->state=Request::RequestCancelled;s.requestComplete(s.requests[b.index].get());
  b.index=(b.index+1)%4;assert(libcamera_source_queue_buffer(&s.src,&b)==0);
  assert(s.camera->queued.back().v[&controls::ExposureValue].ev==0.3f);
  // Cancellation during submission must survive queueRequest's successful return.
  assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_EV,4)==0);
  s.camera->onQueue=[&](Request*r){r->state=Request::RequestCancelled;s.requestComplete(r);};
  assert(libcamera_source_queue_buffer(&s.src,&b)==0);s.camera->onQueue={};
  b.index=(b.index+1)%4;assert(libcamera_source_queue_buffer(&s.src,&b)==0);
  assert(s.camera->queued.back().v[&controls::ExposureValue].ev==0.4f);
  s.camera->supported.clear();assert(libcamera_source_set_control(&s.src,VIDEO_SOURCE_CTRL_EV,0)==0);assert(libcamera_source_queue_buffer(&s.src,&b)==0);assert(s.camera->queued.back().v.empty());
 }
 // Exercise actual stream startup/stop/reset; reconfiguration updates crop bounds.
 if(!bench) {
  libcamera_source life;life.stopping=true;
  assert(libcamera_source_set_control(&life.src,VIDEO_SOURCE_CTRL_ZOOM,200)==0);
  for(int cycle=0;cycle<3;cycle++) {
   life.default_crop={0,0,cycle?1280u:1920u,cycle?720u:1080u};
   libcamera_source_apply_controls(&life,life.controls);
   auto before=life.camera->queued.size();assert(libcamera_source_stream_on(&life.src)==0);
   assert(life.camera->queued.size()==before+4);
   auto expected=cycle?640u:960u;
   assert(life.camera->queued[before].v.at(&controls::ScalerCrop).crop.width==expected);
   assert(life.camera->started.v.at(&controls::ScalerCrop).crop.width==expected);
   assert(life.camera->queued[before+1].v.empty());
   video_buffer frame{0};assert(libcamera_source_queue_buffer(&life.src,&frame)==0);
   assert(life.camera->queued.back().v.empty());
   assert(libcamera_source_stream_off(&life.src)==0);assert(life.requests.empty());
  }
 }
 std::cout<<"PASS: routing, latest updates, no-op setters, errors, stopped-state update, unsupported controls\n";
}
int main(int argc,char**) {bool bench=argc>1;controlTests(bench);lensTests(bench);}
'''
if a.lens_only:code=code.replace('controlTests(bench);lensTests(bench);','lensTests(bench);')
if a.emit:a.emit.write_text(code)
with tempfile.TemporaryDirectory(prefix='pisight-camera-test-') as d:
 src=pathlib.Path(d)/'test.cpp';exe=pathlib.Path(d)/'test';src.write_text(code)
 subprocess.run(['c++','-std=c++17','-O2','-Wall','-Wextra']+(['-DPISIGHT_BENCHMARK'] if a.benchmark else [])+[str(src),'-o',str(exe)],check=True)
 subprocess.run([str(exe)]+(['bench'] if a.benchmark else []),check=True)
