import Foundation

struct CreateRoomResponse: Codable {
    let roomCode: String
    let playerId: String
    let sessionToken: String

    enum CodingKeys: String, CodingKey {
        case roomCode = "room_code"
        case playerId = "player_id"
        case sessionToken = "session_token"
    }
}

struct JoinRoomResponse: Codable {
    let playerId: String
    let sessionToken: String

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case sessionToken = "session_token"
    }
}

struct PlayerInfo: Codable, Identifiable {
    let id: String
    let displayName: String
    let characterName: String?
    let isHost: Bool
    let connectionStatus: String

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case characterName = "character_name"
        case isHost = "is_host"
        case connectionStatus = "connection_status"
    }
}

struct CharacterResponse: Codable {
    let playerId: String
    let characterName: String
    let characterPersonality: String
    let characterBackground: String

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case characterName = "character_name"
        case characterPersonality = "character_personality"
        case characterBackground = "character_background"
    }
}

struct RoomListItem: Codable, Identifiable {
    var id: String { roomCode }
    let roomCode: String
    let status: String
    let playerCount: Int
    let hostName: String?
    let hasPassword: Bool

    enum CodingKeys: String, CodingKey {
        case roomCode = "room_code"
        case status
        case playerCount = "player_count"
        case hostName = "host_name"
        case hasPassword = "has_password"
    }
}

struct RoomInfoResponse: Codable {
    let roomCode: String
    let status: String
    let players: [PlayerInfo]
    let hostPlayerId: String?

    enum CodingKeys: String, CodingKey {
        case roomCode = "room_code"
        case status
        case players
        case hostPlayerId = "host_player_id"
    }
}
