import Foundation

struct CreateRoomResponse: Codable, Sendable {
    let roomCode: String
    let playerId: String
    let sessionToken: String

    enum CodingKeys: String, CodingKey {
        case roomCode = "room_code"
        case playerId = "player_id"
        case sessionToken = "session_token"
    }
}

struct JoinRoomResponse: Codable, Sendable {
    let playerId: String
    let sessionToken: String

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case sessionToken = "session_token"
    }
}

struct PlayerInfo: Codable, Identifiable, Sendable {
    let id: String
    let displayName: String
    let characterName: String?
    let characterPersonality: String?
    let characterBackground: String?
    let isHost: Bool
    let isAI: Bool
    let connectionStatus: String

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case characterName = "character_name"
        case characterPersonality = "character_personality"
        case characterBackground = "character_background"
        case isHost = "is_host"
        case isAI = "is_ai"
        case connectionStatus = "connection_status"
    }

    init(id: String, displayName: String, characterName: String? = nil, characterPersonality: String? = nil, characterBackground: String? = nil, isHost: Bool = false, isAI: Bool = false, connectionStatus: String = "offline") {
        self.id = id
        self.displayName = displayName
        self.characterName = characterName
        self.characterPersonality = characterPersonality
        self.characterBackground = characterBackground
        self.isHost = isHost
        self.isAI = isAI
        self.connectionStatus = connectionStatus
    }
}

struct CharacterResponse: Codable, Sendable {
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

struct RoomListItem: Codable, Identifiable, Sendable {
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

struct RoomInfoResponse: Codable, Sendable {
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
