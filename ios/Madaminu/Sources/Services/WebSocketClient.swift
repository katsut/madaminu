import Foundation
import Observation

@MainActor
@Observable
final class WebSocketClient {
    var isConnected = false

    private var webSocketTask: URLSessionWebSocketTask?
    private var onMessage: ((String, [String: Any]) -> Void)?

    func connect(roomCode: String, token: String, baseURL: String = "wss://REDACTED.example.com") {
        guard let url = URL(string: "\(baseURL)/ws/\(roomCode)?token=\(token)") else { return }

        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        isConnected = true
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

        webSocketTask?.send(.string(jsonString)) { error in
            if let error {
                print("WebSocket send error: \(error)")
            }
        }
    }

    private func receiveLoop() {
        webSocketTask?.receive { [weak self] result in
            Task { @MainActor in
                switch result {
                case .success(let message):
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
                case .failure:
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
