import AVFoundation
import Speech

/// Speech recognition service.
/// All methods must be called from the main thread.
/// Caller is responsible for ensuring main thread execution.
final class SpeechRecognizer: @unchecked Sendable {
    private var _transcript = ""
    private var _isRecording = false
    private var _permissionGranted = false
    private var _errorMessage: String?

    private var audioEngine: AVAudioEngine?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var speechRecognizer: SFSpeechRecognizer?

    var transcript: String { _transcript }
    var isRecording: Bool { _isRecording }
    var permissionGranted: Bool { _permissionGranted }
    var errorMessage: String? { _errorMessage }

    func requestPermission() async {
        let speechStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }

        let audioGranted = await AVAudioApplication.requestRecordPermission()

        await MainActor.run {
            _permissionGranted = speechStatus == .authorized && audioGranted

            if !_permissionGranted {
                _errorMessage = "マイクと音声認識の権限が必要です"
            }

            if _permissionGranted {
                speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "ja-JP"))
            }
        }
    }

    func startRecording(onTranscriptUpdate: @escaping @Sendable (String) -> Void) {
        guard _permissionGranted else {
            _errorMessage = "権限が許可されていません"
            return
        }

        if speechRecognizer == nil {
            speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "ja-JP"))
        }

        guard let speechRecognizer, speechRecognizer.isAvailable else {
            _errorMessage = "音声認識が利用できません"
            return
        }

        stopRecording()

        _transcript = ""
        _errorMessage = nil

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
            _isRecording = true
        } catch {
            _errorMessage = "録音の開始に失敗しました"
            return
        }

        recognitionTask = speechRecognizer.recognitionTask(with: request) { result, error in
            let transcription = result?.bestTranscription.formattedString
            let isFinal = result?.isFinal ?? false
            let hasError = error != nil
            DispatchQueue.main.async { [weak self] in
                guard let self else { return }
                if let transcription {
                    self._transcript = transcription
                    onTranscriptUpdate(transcription)
                }
                if hasError || isFinal {
                    self.stopRecording()
                }
            }
        }
    }

    func stopRecording() {
        audioEngine?.stop()
        audioEngine?.inputNode.removeTap(onBus: 0)  
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()

        audioEngine = nil
        recognitionRequest = nil
        recognitionTask = nil
        _isRecording = false
    }

    func setTranscript(_ value: String) {
        _transcript = value
    }
}
