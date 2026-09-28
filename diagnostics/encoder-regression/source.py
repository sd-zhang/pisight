#!/usr/bin/env python3
"""Compile exact completion/drop/stop functions from production with small camera stubs."""
from pathlib import Path
import subprocess, sys
source = (Path(sys.argv[1]) / 'lib/libcamera-source.cpp').read_text()
def function(name):
    start = source.index(name)
    # Include return type on same line.
    start = source.rfind('\n', 0, start) + 1
    body = source.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]
pre = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cerrno>
#include <cstring>
#include <iostream>
#include <memory>
#include <mutex>
#include <queue>
#include <vector>
#include <unistd.h>
#include <fcntl.h>
#include <sys/time.h>
struct video_buffer { unsigned index, size, bytesused; timeval timestamp; bool error; void *mem; int dmabuf; };
struct video_source { void (*handler)(void*, video_source*, video_buffer*); void *handler_data; int type; void *events; };
constexpr int VIDEO_SOURCE_ENCODED=1, VIDEO_SOURCE_DMABUF=2, EVENT_READ=1;
static int recycled=0, sent=0, destroyed=0;
struct Stream {};
struct Plane { struct FD { int get() { return 1; } } fd; };
struct FrameBuffer { struct Metadata { int64_t timestamp=0; struct P {unsigned bytesused;}; std::vector<P> planes() {return {{1}};} }; Metadata metadata(){return {};}; std::vector<Plane> planes(){return {{}};} };
struct StreamInfo {};
struct Request { enum {RequestCancelled}; int status(){return 1;} unsigned cookie(){return 0;} std::vector<std::pair<int,FrameBuffer*>> buffers(){return {{0,nullptr}};} };
struct Config { struct C { Stream *stream(){return nullptr;} }; C at(int){return {};} };
struct Camera { void stop(){}; };
struct Span { void *data(){return nullptr;} };
struct MjpegEncoder { ~MjpegEncoder(){++destroyed;} StreamInfo getStreamInfo(Stream*){return {};}; void EncodeBuffer(void*,int,void*,unsigned,StreamInfo,int64_t,unsigned){}; };
struct libcamera_source { video_source src; std::queue<Request*> completed_requests; std::queue<video_buffer> encoded_buffers; std::mutex completion_mutex; std::atomic<bool> stopping{false}; std::atomic<bool> pipe_error_logged{false}; uint64_t encoded_frames=0,dropped_frames=0; int pfds[2]; Config *config; Camera *camera; MjpegEncoder *encoder; std::vector<std::unique_ptr<Request>> requests; struct B {video_buffer *buffers;} buffers; std::vector<std::pair<FrameBuffer*,Span>> mapped_buffers_; void notifyCompletion(); void pipeError(const char*,int); void requestComplete(Request*); void outputReady(void*,size_t,int64_t,unsigned); };
static int interrupted_reads=0, interrupted_writes=0;
static ssize_t test_write(int fd,const void *buf,size_t n) {
 if (interrupted_writes) {--interrupted_writes;errno=EINTR;return -1;} return ::write(fd,buf,n);
}
static ssize_t test_read(int fd,void *buf,size_t n) {
 if (interrupted_reads) {--interrupted_reads;errno=EINTR;return -1;} return ::read(fd,buf,n);
}
#define read test_read
#define write test_write
#define to_libcamera_source(s) reinterpret_cast<libcamera_source*>(s)
static void events_unwatch_fd(void*,int,int){}
static int libcamera_source_queue_buffer(video_source*,video_buffer*) {++recycled; return 0;}
'''
# The unrelated camera encoding half needs libcamera types. Execute the exact
# production event completion branch, stopping at its request-processing boundary.
proc = function('static void libcamera_source_video_process(void *d)')
proc = proc[:proc.index('\n\t/* We have only a single buffer')] + '\n}\n'
# No request-processing branch is taken by these output ownership tests.
if 'void libcamera_source::notifyCompletion' in source:
    pre += function('void libcamera_source::pipeError') + function('void libcamera_source::notifyCompletion')
pre += '\n'.join([function('void libcamera_source::requestComplete'), function('void libcamera_source::outputReady'),proc,function('static int libcamera_source_stream_off')])
pre += r'''
int main() {
 libcamera_source s; Config config; Camera camera;
 s.config=&config; s.camera=&camera; s.encoder=new MjpegEncoder;
 s.src.type=VIDEO_SOURCE_ENCODED; s.src.handler=[](void*,video_source*,video_buffer*b){ assert(b->bytesused); ++sent; };
 assert(pipe2(s.pfds,O_NONBLOCK)==0);
 // zero failure returns the same source/destination slot without UVC submission
 interrupted_writes=1; interrupted_reads=1;
 s.outputReady(nullptr,0,123,7); libcamera_source_video_process(&s);
 assert(recycled==1 && sent==0 && s.dropped_frames==1);
 // the next successful frame advances normally after a failed frame
 s.outputReady(nullptr,6,124,7); libcamera_source_video_process(&s);
 assert(recycled==1 && sent==1);
 // An empty nonblocking pipe must not pop an unnotified completion.
 video_buffer pending={}; s.encoded_buffers.push(pending);
 libcamera_source_video_process(&s); assert(s.encoded_buffers.size()==1);
 s.encoded_buffers.pop();
 // request completion notifications also retry interruption.
 Request completed; interrupted_writes=1; s.requestComplete(&completed);
 assert(s.completed_requests.size()==1); char notification;
 assert(read(s.pfds[0],&notification,1)==1); s.completed_requests.pop();
 // pending notifications are drained before request destruction/reopen
 s.outputReady(nullptr,0,125,7); Request request; s.requestComplete(&request);
 interrupted_reads=1; libcamera_source_stream_off(&s.src);
 assert(s.stopping && s.encoder==nullptr && destroyed==1);
 assert(s.completed_requests.empty() && s.encoded_buffers.empty());
 char b; assert(read(s.pfds[0],&b,1)==-1);
 s.outputReady(nullptr,6,126,7); assert(s.encoded_buffers.empty());
 close(s.pfds[0]);close(s.pfds[1]);
 std::cout << "source zero-drop/success/EINTR/empty-read/stop-drain: PASS\n";
}
'''
Path('/tmp/encoder-source-test.cpp').write_text(pre)
subprocess.run(['c++','-std=c++17','-pthread','/tmp/encoder-source-test.cpp','-o','/tmp/encoder-source-test'],check=True)
subprocess.run(['/tmp/encoder-source-test'],check=True)
