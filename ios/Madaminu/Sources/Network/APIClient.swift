import Foundation

enum APIError: Error {
    case invalidURL
    case requestFailed(statusCode: Int, message: String)
    case decodingFailed
    case networkError(Error)
}

actor APIClient {
    static let defaultBaseURL = "https://murder-production.up.railway.app"

    let baseURL: String

    init(baseURL: String = APIClient.defaultBaseURL) {
        self.baseURL = baseURL
    }

    func listRooms() async throws -> [RoomListItem] {
        return try await get("/api/v1/rooms")
    }

    func createRoom(displayName: String, password: String? = nil) async throws -> CreateRoomResponse {
        var body = ["display_name": displayName]
        if let password, !password.isEmpty {
            body["password"] = password
        }
        return try await post("/api/v1/rooms", body: body)
    }

    func joinRoom(roomCode: String, displayName: String, password: String? = nil) async throws -> JoinRoomResponse {
        var body = ["display_name": displayName]
        if let password, !password.isEmpty {
            body["password"] = password
        }
        return try await post("/api/v1/rooms/\(roomCode)/join", body: body)
    }

    func getRoomInfo(roomCode: String) async throws -> RoomInfoResponse {
        return try await get("/api/v1/rooms/\(roomCode)")
    }

    func startGame(roomCode: String, sessionToken: String) async throws {
        guard let url = URL(string: baseURL + "/api/v1/rooms/\(roomCode)/start") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 120
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(sessionToken, forHTTPHeaderField: "X-Session-Token")

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response, data: data)
    }

    func createCharacter(
        roomCode: String,
        sessionToken: String,
        name: String,
        gender: String,
        age: String,
        occupation: String,
        appearance: String,
        personality: String,
        background: String
    ) async throws -> CharacterResponse {
        let body: [String: String] = [
            "character_name": name,
            "character_gender": gender,
            "character_age": age,
            "character_occupation": occupation,
            "character_appearance": appearance,
            "character_personality": personality,
            "character_background": background,
        ]
        return try await post(
            "/api/v1/rooms/\(roomCode)/characters",
            body: body,
            headers: ["X-Session-Token": sessionToken]
        )
    }

    func getDebugInfo(roomCode: String, sessionToken: String) async throws -> DebugInfoResponse {
        return try await get("/api/v1/rooms/\(roomCode)/debug", headers: ["X-Session-Token": sessionToken])
    }

    private func get<T: Decodable>(_ path: String, headers: [String: String] = [:]) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response, data: data)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func post<T: Decodable>(
        _ path: String,
        body: [String: String],
        headers: [String: String] = [:]
    ) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response, data: data)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func validateResponse(_ response: URLResponse, data: Data) throws {
        guard let httpResponse = response as? HTTPURLResponse else { return }
        guard (200...299).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }
    }
}
