// Compile this harness with the actual patched hw_mjpeg_encoder.cpp.
#include <atomic>
#include <chrono>
#include <memory>
#include <string>
#include <thread>
#include <iostream>
#include <cstdarg>
#include <cstring>
#include <cerrno>
#include <linux/videodev2.h>
#define private public
#include "hw_mjpeg_encoder.hpp"
#undef private
static std::string mode;
static int queues, dequeues, closes;
static uint8_t jpeg[16] = {0xff, 0xd8, 1, 2, 0xff, 0xd9};
extern "C" int __wrap_open(const char *, int, ...) { return 43; }
extern "C" void *__wrap_mmap(void *, size_t, int, int, int, long) { return jpeg; }
extern "C" int __wrap_close(int) { ++closes; return 0; }
extern "C" int __wrap_munmap(void *, size_t) { return 0; }
extern "C" int __wrap_ioctl(int, unsigned long op, ...) {
 va_list ap; va_start(ap, op); void *arg = va_arg(ap, void *); va_end(ap);
 if (op == VIDIOC_S_FMT) {
  auto *f = static_cast<v4l2_format *>(arg);
  f->fmt.pix_mp.plane_fmt[0].bytesperline = 8;
  f->fmt.pix_mp.plane_fmt[0].sizeimage = 32;
 }
 if (op == VIDIOC_QUERYBUF) static_cast<v4l2_buffer *>(arg)->m.planes[0].length = sizeof(jpeg);
 if (op == VIDIOC_QBUF) {
  ++queues;
  if ((mode == "qout" && queues == 1) || ((mode == "qcap" || mode == "recover") && queues == 2)) { errno = EIO; return -1; }
 }
 if (op == VIDIOC_DQBUF) {
  ++dequeues;
  if (mode == "timeout" || mode == "cancel") { errno = EAGAIN; return -1; }
  if ((mode == "dout" && dequeues == 1) || (mode == "dcap" && dequeues == 2)) { errno = EIO; return -1; }
  auto *b = static_cast<v4l2_buffer *>(arg);
  if (mode == "input_error" && b->type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE) b->flags |= V4L2_BUF_FLAG_ERROR;
  if (b->type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE) {
   b->m.planes[0].bytesused = 6;
   if (mode == "error") b->flags |= V4L2_BUF_FLAG_ERROR;
   if (mode == "zero") b->m.planes[0].bytesused = 0;
   if (mode == "length") b->m.planes[0].bytesused = 1000;
   if (mode == "offset") b->m.planes[0].data_offset = 7;
   if (mode == "index") b->index = 1;
   if (mode == "truncated") jpeg[5] = 0;
  }
 }
 return 0;
}
int main(int argc, char **argv) {
 mode = argc > 1 ? argv[1] : "ok";
 HwMjpegEncoder encoder(42, "/fake-codec", 72);
 encoder.configured_ = encoder.streaming_ = true;
 encoder.cap_buf_.mem = jpeg; encoder.cap_buf_.length = sizeof(jpeg);
 encoder.out_sizeimage_ = 32;
 uint8_t dest[16]; memset(dest, 0x55, sizeof(dest));
 auto start = std::chrono::steady_clock::now();
 std::thread cancel;
#ifndef BASELINE
 if (mode == "cancel") cancel = std::thread([&] { std::this_thread::sleep_for(std::chrono::milliseconds(20)); encoder.Cancel(); });
#endif
 size_t n = encoder.Encode(7, 8, 8, 8, dest, mode == "small" ? 5 : sizeof(dest));
 if (cancel.joinable()) cancel.join();
 auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();
 bool ok = mode == "ok" ? n == 6 && memcmp(dest, jpeg, 6) == 0 : n == 0 && dest[0] == 0x55;
 if (mode == "qout" || mode == "qcap" || mode == "dout" || mode == "dcap" || mode == "timeout" || mode == "cancel")
  ok &= !encoder.configured_ && encoder.fd_ == -1 && closes == 1;
 if (mode == "recover") {
  ok &= !encoder.configured_ && encoder.fd_ == -1 && closes == 1;
  mode = "ok";
  ok &= encoder.Configure(8,8,8);
  ok &= encoder.Encode(7,8,8,8,dest,sizeof(dest)) == 6;
  mode = "recover";
 }
 if (mode == "timeout") ok &= ms >= 900 && ms < 1500;
 if (mode == "cancel") ok &= ms < 200;
 std::cout << mode << ": " << (ok ? "PASS" : "FAIL") << " bytes=" << n << " elapsed_ms=" << ms << " closes=" << closes << '\n';
 return ok ? 0 : 1;
}
