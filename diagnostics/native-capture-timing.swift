import Foundation
import AVFoundation
import CoreMedia
import CoreVideo
import CryptoKit

final class Counter: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate, AVCaptureAudioDataOutputSampleBufferDelegate {
    let video: AVCaptureVideoDataOutput
    var videoPTS: [Double] = []
    var audioPackets: [(Double, Int, Double)] = []
    var droppedVideo = 0
    var videoHashes: Set<String> = []
    var previousHash = ""
    var repeatedVideo = 0
    var videoArrival: [Double] = []
    var changedFrameWallTimes: [Double] = []
    var dimensions: Set<String> = []
    init(_ video: AVCaptureVideoDataOutput) { self.video = video }
    func captureOutput(_ output: AVCaptureOutput, didOutput sample: CMSampleBuffer, from connection: AVCaptureConnection) {
        let pts = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sample))
        if output === video {
            videoPTS.append(pts)
            videoArrival.append(ProcessInfo.processInfo.systemUptime)
            if let pixel = CMSampleBufferGetImageBuffer(sample) {
                dimensions.insert("\(CVPixelBufferGetWidth(pixel))x\(CVPixelBufferGetHeight(pixel))")
                CVPixelBufferLockBaseAddress(pixel, .readOnly)
                if let base = CVPixelBufferGetBaseAddress(pixel) {
                    // Packed UYVY: hash visible pixels only, excluding row padding.
                    var hasher = SHA256()
                    for row in 0..<CVPixelBufferGetHeight(pixel) {
                        hasher.update(data: Data(bytesNoCopy: base.advanced(by: row * CVPixelBufferGetBytesPerRow(pixel)), count: CVPixelBufferGetWidth(pixel) * 2, deallocator: .none))
                    }
                    let hash = hasher.finalize().description
                    videoHashes.insert(hash)
                    if hash == previousHash { repeatedVideo += 1 }
                    else { changedFrameWallTimes.append(Date().timeIntervalSince1970) }
                    previousHash = hash
                }
                CVPixelBufferUnlockBaseAddress(pixel, .readOnly)
            }
        }
        else {
            let format = CMSampleBufferGetFormatDescription(sample)!
            let rate = CMAudioFormatDescriptionGetStreamBasicDescription(format)!.pointee.mSampleRate
            audioPackets.append((pts, CMSampleBufferGetNumSamples(sample), rate))
        }
    }
    func captureOutput(_ output: AVCaptureOutput, didDrop sample: CMSampleBuffer, from connection: AVCaptureConnection) { droppedVideo += 1 }
    func report() -> [String: Any] {
        var result: [String: Any] = ["video_frames": videoPTS.count, "video_drop_callbacks": droppedVideo, "audio_packets": audioPackets.count]
        result["video_unique_hashes"] = videoHashes.count
        result["video_consecutive_repeats"] = repeatedVideo
        result["video_dimensions"] = dimensions.sorted()
        result["video_changed_frame_unix_times"] = changedFrameWallTimes
        if let first = videoArrival.first, let last = videoArrival.last, last > first {
            result["video_arrival_span_seconds"] = last - first
            result["video_unique_fps"] = Double(max(0, videoHashes.count - 1)) / (last - first)
            result["video_max_arrival_gap_ms"] = zip(videoArrival.dropFirst(), videoArrival).map { ($0 - $1) * 1000 }.max()!
        }
        if let first = videoPTS.first, let last = videoPTS.last, videoPTS.count > 1 {
            let gaps = zip(videoPTS.dropFirst(), videoPTS).map { $0 - $1 }.sorted()
            result["video_span_seconds"] = last-first
            result["video_fps"] = Double(videoPTS.count-1)/(last-first)
            result["video_median_gap_ms"] = gaps[gaps.count/2]*1000
            result["video_max_gap_ms"] = gaps.last!*1000
        }
        if let first = audioPackets.first, let last = audioPackets.last {
            let gaps = zip(audioPackets.dropFirst(), audioPackets).map { $0.0 - ($1.0 + Double($1.1)/$1.2) }
            result["audio_samples"] = audioPackets.reduce(0) { $0 + $1.1 }
            result["audio_sample_rate"] = first.2
            result["audio_span_seconds"] = last.0+Double(last.1)/last.2-first.0
            result["audio_gaps_over_1ms"] = gaps.filter { abs($0)>0.001 }.count
            result["audio_max_gap_ms"] = (gaps.map { abs($0) }.max() ?? 0)*1000
        }
        return result
    }
}

do {
    let seconds = CommandLine.arguments.count > 1 ? Double(CommandLine.arguments[1])! : 15
    let withAudio = !CommandLine.arguments.contains("--video-only")
    let outputPath = ProcessInfo.processInfo.environment["PISIGHT_RESULT"] ?? "/private/tmp/pisight-pwm-test/native-results.json"
    let started = ISO8601DateFormatter().string(from: Date())
    guard let camera = AVCaptureDevice.devices(for: .video).first(where: {$0.localizedName == "iSight"}) else {
        fatalError("Named PiSight camera unavailable")
    }
    let session = AVCaptureSession()
    let video = AVCaptureVideoDataOutput()
    video.alwaysDiscardsLateVideoFrames = false
    video.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_422YpCbCr8,
                           kCVPixelBufferWidthKey as String: 1280,
                           kCVPixelBufferHeightKey as String: 720]
    let audio = AVCaptureAudioDataOutput()
    let counter = Counter(video)
    let queue = DispatchQueue(label: "pisight.capture.counter", qos: .userInitiated)
    video.setSampleBufferDelegate(counter, queue: queue)
    audio.setSampleBufferDelegate(counter, queue: queue)
    session.beginConfiguration()
    if session.canSetSessionPreset(.hd1280x720) { session.sessionPreset = .hd1280x720 }
    let cameraInput = try AVCaptureDeviceInput(device: camera)
    guard session.canAddInput(cameraInput), session.canAddOutput(video) else { fatalError("Capture session cannot accept video input/output") }
    session.addInput(cameraInput)
    session.addOutput(video)
    if withAudio {
        let micName = ProcessInfo.processInfo.environment["PISIGHT_MIC_NAME"] ?? "iSight Microphone"
        guard let mic = AVCaptureDevice.devices(for: .audio).first(where: {$0.localizedName == micName}) else { fatalError("Named PiSight microphone unavailable: \(micName)") }
        let micInput = try AVCaptureDeviceInput(device: mic)
        guard session.canAddInput(micInput), session.canAddOutput(audio) else { fatalError("Capture session cannot accept audio input/output") }
        session.addInput(micInput)
        session.addOutput(audio)
    }
    session.commitConfiguration()
    guard let format = camera.formats.first(where: {
        let dim = CMVideoFormatDescriptionGetDimensions($0.formatDescription)
        return dim.width == 1280 && dim.height == 720 && $0.videoSupportedFrameRateRanges.contains(where: {$0.minFrameRate <= 30.1 && $0.maxFrameRate >= 29.9})
    }) else { fatalError("PiSight has no 1280x720/30 format") }
    try camera.lockForConfiguration()
    camera.activeFormat = format
    let duration = format.videoSupportedFrameRateRanges.first(where: {$0.minFrameRate <= 30.1 && $0.maxFrameRate >= 29.9})!.minFrameDuration
    camera.activeVideoMinFrameDuration = duration
    camera.activeVideoMaxFrameDuration = duration
    print("Selected format: \(format)")
    camera.unlockForConfiguration()
    print("Capturing named iSight; audio enabled: \(withAudio); started \(started)")
    session.startRunning()
    print("Active format after start: \(camera.activeFormat)")
    RunLoop.current.run(until: Date(timeIntervalSinceNow: seconds))
    session.stopRunning()
    var report = queue.sync { counter.report() }
    report["started_utc"] = started
    report["camera_id"] = camera.uniqueID
    report["audio_enabled"] = withAudio
    report["requested_seconds"] = seconds
    report["active_format"] = camera.activeFormat.description
    let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: URL(fileURLWithPath: outputPath))
    print(String(data: data, encoding: .utf8)!)
} catch { fputs("Capture failed: \(error)\n", stderr); exit(1) }
