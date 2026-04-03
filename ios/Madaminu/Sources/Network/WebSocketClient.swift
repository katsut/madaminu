import Foundation
import os

final class WebSocketClient: Sendable {
    private let lock = NSLock()

    private struct State {
        var webSocketTask: URLSessionWebSocketTask?
        var onMessage: (@Sendable (String, [String: String]) -> Void)?
        var onStateChange: (@Sendable (Bool, String?) -> Void)?
        var roomCode: String?
        var token: String?
        var baseURLString: String?
        var retryCount = 0
        var intentionalDisconnect = false
        var receiveTask: Task<Void, Never>?
        var pingTask: Task<Void, Never>?
    }

    private let state = NSLockProtected(State())
    private let maxRetries = 10
    private let logger = Logger(subsystem: "com.katsut.madaminu", category: "WebSocket")

    init() {}

    func connect(roomCode: String, token: String, baseURL: String = "ws://127.0.0.1:8000") {
        state.write {
            $0.roomCode = roomCode
            $0.token = token
            $0.baseURLString = baseURL
            $0.retryCount = 0
            $0.intentionalDisconnect = false
        }
        performConnect()
    }

    func disconnect() {
        let task = state.write { s -> URLSessionWebSocketTask? in
            s.intentionalDisconnect = true
            s.receiveTask?.cancel()
            s.receiveTask = nil
            s.pingTask?.cancel()
            s.pingTask = nil
            let t = s.webSocketTask
            s.webSocketTask = nil
            return t
        }
        task?.cancel(with: .goingAway, reason: nil)
        notifyStateChange(connected: false, error: nil)
    }

    func setMessageHandler(_ handler: @escaping @Sendable (String, [String: String]) -> Void) {
        state.write { $0.onMessage = handler }
    }

    func setStateChangeHandler(_ handler: @escaping @Sendable (Bool, String?) -> Void) {
        state.write { $0.onStateChange = handler }
    }

    func send(type: String, data: [String: String] = [:]) {
        let message: [String: Any] = ["type": type, "data": data]
        guard let jsonData = try? JSONSerialization.data(withJSONObject: message),
              let jsonString = String(data: jsonData, encoding: .utf8) else { return }

        print("[WS] send: \(type)")
        let task = state.read { $0.webSocketTask }

        Task { [jsonString] in
            try? await task?.send(.string(jsonString))
        }
    }

    private func performConnect() {
        let params = state.read { s -> (String, String, String)? in
            guard let rc = s.roomCode, let tk = s.token, let bu = s.baseURLString else { return nil }
            return (rc, tk, bu)
        }

        guard let (roomCode, token, baseURLString) = params else { return }

        guard let url = URL(string: "\(baseURLString)/ws/\(roomCode)?token=\(token)") else {
            notifyStateChange(connected: false, error: "Invalid WebSocket URL")
            return
        }

        let session = URLSession(configuration: .default)
        let newTask = session.webSocketTask(with: url)

        state.write { $0.webSocketTask = newTask }

        newTask.resume()
        logger.info("Connecting to \(url)")
        notifyStateChange(connected: true, error: nil)
        startReceiveLoop()
        startPingLoop()
    }

    private func startReceiveLoop() {
        let (task, handler) = state.write { s -> (URLSessionWebSocketTask?, (@Sendable (String, [String: String]) -> Void)?) in
            s.receiveTask?.cancel()
            let t = s.webSocketTask
            let h = s.onMessage
            s.receiveTask = nil
            return (t, h)
        }

        guard let task else { return }

        let receiveTask = Task { [weak self] in
            guard let self else { return }
            await self.receiveLoop(task: task, handler: handler)
        }

        state.write { $0.receiveTask = receiveTask }
    }

    private func startPingLoop() {
        state.write { s in
            s.pingTask?.cancel()
            s.pingTask = Task { [weak self] in
                while !Task.isCancelled {
                    try? await Task.sleep(for: .seconds(30))
                    guard !Task.isCancelled, let self else { return }
                    let task = self.state.read { $0.webSocketTask }
                    task?.sendPing { _ in }
                }
            }
        }
    }

    private func receiveLoop(task: URLSessionWebSocketTask, handler: (@Sendable (String, [String: String]) -> Void)?) async {
        while !Task.isCancelled {
            do {
                let message = try await task.receive()
                switch message {
                case .string(let text):
                    parseAndDeliver(text, handler: handler)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        parseAndDeliver(text, handler: handler)
                    }
                @unknown default:
                    break
                }
            } catch {
                if Task.isCancelled { return }
                logger.error("Connection error: \(error.localizedDescription)")
                notifyStateChange(connected: false, error: error.localizedDescription)
                await attemptReconnect()
                return
            }
        }
    }

    private func parseAndDeliver(_ text: String, handler: (@Sendable (String, [String: String]) -> Void)?) {
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

    private func notifyStateChange(connected: Bool, error: String?) {
        let handler = state.read { $0.onStateChange }
        handler?(connected, error)
    }

    private func attemptReconnect() async {
        let (shouldReconnect, currentRetry) = state.write { s -> (Bool, Int) in
            let should = !s.intentionalDisconnect && s.retryCount < maxRetries
            let retry = s.retryCount
            if should { s.retryCount += 1 }
            return (should, retry)
        }

        guard shouldReconnect else {
            let isIntentional = state.read { $0.intentionalDisconnect }
            if !isIntentional {
                logger.warning("Max reconnection attempts reached")
                notifyStateChange(connected: false, error: "接続に失敗しました。再試行してください。")
            }
            return
        }

        let delay = min(UInt64(pow(2.0, Double(currentRetry + 1))), 30)
        logger.info("Reconnecting in \(delay)s (attempt \(currentRetry + 1)/\(self.maxRetries))")

        try? await Task.sleep(for: .seconds(delay))

        let stillShouldReconnect = state.read { !$0.intentionalDisconnect }

        if stillShouldReconnect {
            performConnect()
        }
    }
}

/// Thread-safe wrapper around a value protected by NSLock
private final class NSLockProtected<Value>: @unchecked Sendable {
    private var value: Value
    private let lock = NSLock()

    init(_ value: Value) {
        self.value = value
    }

    func read<T>(_ body: (Value) -> T) -> T {
        lock.withLock { body(value) }
    }

    @discardableResult
    func write<T>(_ body: (inout Value) -> T) -> T {
        lock.withLock { body(&value) }
    }
}
