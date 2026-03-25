import Foundation
import Observation
import os

@Observable
final class WebSocketClient: @unchecked Sendable {
    @MainActor var isConnected = false
    @MainActor var connectionError: String?

    private let lock = NSLock()

    private var _webSocketTask: URLSessionWebSocketTask?
    private var _onMessage: (@Sendable (String, [String: String]) -> Void)?
    private var _roomCode: String?
    private var _token: String?
    private var _baseURLString: String?
    private var _retryCount = 0
    private var _intentionalDisconnect = false
    private var _receiveTask: Task<Void, Never>?

    private let maxRetries = 3
    private let logger = Logger(subsystem: "com.katsut.madaminu", category: "WebSocket")

    nonisolated init() {}

    func connect(roomCode: String, token: String, baseURL: String = "wss://murder-production.up.railway.app") {
        lock.withLock {
            _roomCode = roomCode
            _token = token
            _baseURLString = baseURL
            _retryCount = 0
            _intentionalDisconnect = false
        }

        performConnect()
    }

    func disconnect() {
        let task: URLSessionWebSocketTask? = lock.withLock {
            _intentionalDisconnect = true
            let t = _webSocketTask
            _receiveTask?.cancel()
            _receiveTask = nil
            _webSocketTask = nil
            return t
        }

        task?.cancel(with: .goingAway, reason: nil)

        Task { @MainActor in
            self.isConnected = false
        }
    }

    func setMessageHandler(_ handler: @escaping @Sendable (String, [String: String]) -> Void) {
        lock.withLock {
            _onMessage = handler
        }
    }

    func send(type: String, data: [String: String] = [:]) {
        let message: [String: Any] = ["type": type, "data": data]
        guard let jsonData = try? JSONSerialization.data(withJSONObject: message),
              let jsonString = String(data: jsonData, encoding: .utf8) else { return }

        let task: URLSessionWebSocketTask? = lock.withLock { _webSocketTask }

        Task { [jsonString] in
            try? await task?.send(.string(jsonString))
        }
    }

    private func performConnect() {
        let params: (String, String, String)? = lock.withLock {
            guard let rc = _roomCode, let tk = _token, let bu = _baseURLString else { return nil }
            return (rc, tk, bu)
        }

        guard let (roomCode, token, baseURLString) = params else { return }

        guard let url = URL(string: "\(baseURLString)/ws/\(roomCode)?token=\(token)") else {
            Task { @MainActor in
                self.connectionError = "Invalid WebSocket URL"
            }
            return
        }

        Task { @MainActor in
            self.connectionError = nil
        }

        let session = URLSession(configuration: .default)
        let newTask = session.webSocketTask(with: url)

        lock.withLock {
            _webSocketTask = newTask
        }

        newTask.resume()
        logger.info("Connecting to \(url)")

        Task { @MainActor in
            self.isConnected = true
        }

        startReceiveLoop()
    }

    private func startReceiveLoop() {
        lock.withLock {
            _receiveTask?.cancel()
            let task = _webSocketTask
            let handler = _onMessage
            _receiveTask = Task { [weak self] in
                guard let self, let task else { return }
                await self.receiveLoop(task: task, handler: handler)
            }
        }
    }

    private func receiveLoop(task: URLSessionWebSocketTask, handler: (@Sendable (String, [String: String]) -> Void)?) async {
        while !Task.isCancelled {
            do {
                let message = try await task.receive()
                switch message {
                case .string(let text):
                    handleRawMessage(text, handler: handler)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        handleRawMessage(text, handler: handler)
                    }
                @unknown default:
                    break
                }
            } catch {
                if Task.isCancelled { return }
                logger.error("Connection error: \(error.localizedDescription)")

                await MainActor.run {
                    self.connectionError = error.localizedDescription
                    self.isConnected = false
                }

                await attemptReconnect()
                return
            }
        }
    }

    private nonisolated func handleRawMessage(_ text: String, handler: (@Sendable (String, [String: String]) -> Void)?) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        let rawData = json["data"] as? [String: Any] ?? [:]
        var stringData: [String: String] = [:]
        for (key, value) in rawData {
            if let str = value as? String {
                stringData[key] = str
            } else if let num = value as? NSNumber {
                stringData[key] = num.stringValue
            } else if let jsonObj = value as? [String: Any],
                      let jsonData = try? JSONSerialization.data(withJSONObject: jsonObj),
                      let jsonStr = String(data: jsonData, encoding: .utf8) {
                stringData[key] = jsonStr
            } else if let jsonArr = value as? [Any],
                      let jsonData = try? JSONSerialization.data(withJSONObject: jsonArr),
                      let jsonStr = String(data: jsonData, encoding: .utf8) {
                stringData[key] = jsonStr
            }
        }

        handler?(type, stringData)
    }

    private func attemptReconnect() async {
        let (shouldReconnect, currentRetry) = lock.withLock {
            let should = !_intentionalDisconnect && _retryCount < maxRetries
            let retry = _retryCount
            if should { _retryCount += 1 }
            return (should, retry)
        }

        guard shouldReconnect else {
            let isIntentional = lock.withLock { _intentionalDisconnect }
            if !isIntentional {
                logger.warning("Max reconnection attempts reached")
                await MainActor.run {
                    self.connectionError = "接続に失敗しました。再試行してください。"
                }
            }
            return
        }

        let delay = UInt64(pow(2.0, Double(currentRetry + 1)))
        logger.info("Reconnecting in \(delay)s (attempt \(currentRetry + 1)/\(self.maxRetries))")

        try? await Task.sleep(for: .seconds(delay))

        let stillShouldReconnect = lock.withLock { !_intentionalDisconnect }

        if stillShouldReconnect {
            performConnect()
        }
    }
}
