import Foundation
import Observation

@MainActor
@Observable
final class WebSocketClient {
    var isConnected = false

    private var webSocketTask: URLSessionWebSocketTask?
    private var onMessage: ((String, [String: Any]) -> Void)?

    var connectionError: String?

    func connect(roomCode: String, token: String, baseURL: String = "wss://murder-production.up.railway.app") {
        guard let url = URL(string: "\(baseURL)/ws/\(roomCode)?token=\(token)") else {
            connectionError = "Invalid WebSocket URL"
            return
        }

        connectionError = nil
        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        isConnected = true
        print("[WS] Connecting to \(url)")
        receiveLoop()
    }

    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        isConnected = false
    }

    func setMessageHandler(_ handler: @escaping (String, [String: Any]) -> Void) {
        onMessage = handler
    }

    func send(type: String, data: [String: Any] = [:]) {
        let message: [String: Any] = ["type": type, "data": data]
        guard let jsonData = try? JSONSerialization.data(withJSONObject: message),
              let jsonString = String(data: jsonData, encoding: .utf8) else { return }

        let task = webSocketTask
        Task.detached {
            try? await task?.send(.string(jsonString))
        }
    }

    private func receiveLoop() {
        let task = webSocketTask
        Task.detached { [weak self] in
            guard let task else { return }
            do {
                let message = try await task.receive()
                await MainActor.run {
                    switch message {
                    case .string(let text):
                        self?.handleMessage(text)
                    case .data(let data):
                        if let text = String(data: data, encoding: .utf8) {
                            self?.handleMessage(text)
                        }
                    @unknown default:
                        break
                    }
                    self?.receiveLoop()
                }
            } catch {
                await MainActor.run {
                    print("[WS] Connection error: \(error)")
                    self?.connectionError = error.localizedDescription
                    self?.isConnected = false
                }
            }
        }
    }

    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        let messageData = json["data"] as? [String: Any] ?? [:]
        onMessage?(type, messageData)
    }
}
