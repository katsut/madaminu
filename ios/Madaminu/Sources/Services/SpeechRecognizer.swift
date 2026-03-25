import AVFoundation
import Observation
import Speech

@MainActor
@Observable
final class SpeechRecognizer {
    var transcript = ""
    var isRecording = false
    var permissionGranted = false
    var errorMessage: String?

    private var audioEngine: AVAudioEngine?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "ja-JP"))

    func requestPermission() async {
        let speechStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }

        let audioGranted = await AVAudioApplication.requestRecordPermission()

        permissionGranted = speechStatus == .authorized && audioGranted

        if !permissionGranted {
            errorMessage = "マイクと音声認識の権限が必要です"
        }
    }

    func startRecording() {
        guard permissionGranted else {
            errorMessage = "権限が許可されていません"
            return
        }
        guard let speechRecognizer, speechRecognizer.isAvailable else {
            errorMessage = "音声認識が利用できません"
            return
        }

        stopRecording()

        transcript = ""
        errorMessage = nil

        let audioEngine = AVAudioEngine()
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true

        self.audioEngine = audioEngine
        self.recognitionRequest = request

        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            request.append(buffer)
        }

        audioEngine.prepare()

        do {
            try audioEngine.start()
            isRecording = true
        } catch {
            errorMessage = "録音の開始に失敗しました"
            return
        }

        recognitionTask = speechRecognizer.recognitionTask(with: request) { [weak self] result, error in
            Task { @MainActor in
                if let result {
                    self?.transcript = result.bestTranscription.formattedString
                }

                if error != nil || (result?.isFinal ?? false) {
                    self?.stopRecordingInternal()
                }
            }
        }
    }

    func stopRecording() {
        stopRecordingInternal()
    }

    private func stopRecordingInternal() {
        audioEngine?.stop()
        audioEngine?.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()

        audioEngine = nil
        recognitionRequest = nil
        recognitionTask = nil
        isRecording = false
    }
}
