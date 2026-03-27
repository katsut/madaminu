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
    let characterNameKana: String?
    let characterGender: String?
    let characterAge: String?
    let characterOccupation: String?
    let characterAppearance: String?
    let characterPersonality: String?
    let characterBackground: String?
    let publicInfo: String?
    let portraitUrl: String?
    let isHost: Bool
    let isAI: Bool
    let isReady: Bool
    let connectionStatus: String

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case characterName = "character_name"
        case characterNameKana = "character_name_kana"
        case characterGender = "character_gender"
        case characterAge = "character_age"
        case characterOccupation = "character_occupation"
        case characterAppearance = "character_appearance"
        case characterPersonality = "character_personality"
        case characterBackground = "character_background"
        case publicInfo = "public_info"
        case portraitUrl = "portrait_url"
        case isHost = "is_host"
        case isAI = "is_ai"
        case isReady = "is_ready"
        case connectionStatus = "connection_status"
    }

    init(id: String, displayName: String, characterName: String? = nil, characterNameKana: String? = nil, characterGender: String? = nil, characterAge: String? = nil, characterOccupation: String? = nil, characterAppearance: String? = nil, characterPersonality: String? = nil, characterBackground: String? = nil, publicInfo: String? = nil, portraitUrl: String? = nil, isHost: Bool = false, isAI: Bool = false, isReady: Bool = false, connectionStatus: String = "offline") {
        self.id = id
        self.displayName = displayName
        self.characterName = characterName
        self.characterNameKana = characterNameKana
        self.characterGender = characterGender
        self.characterAge = characterAge
        self.characterOccupation = characterOccupation
        self.characterAppearance = characterAppearance
        self.characterPersonality = characterPersonality
        self.characterBackground = characterBackground
        self.publicInfo = publicInfo
        self.portraitUrl = portraitUrl
        self.isHost = isHost
        self.isAI = isAI
        self.isReady = isReady
        self.connectionStatus = connectionStatus
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        displayName = try container.decode(String.self, forKey: .displayName)
        characterName = try container.decodeIfPresent(String.self, forKey: .characterName)
        characterNameKana = try container.decodeIfPresent(String.self, forKey: .characterNameKana)
        characterGender = try container.decodeIfPresent(String.self, forKey: .characterGender)
        characterAge = try container.decodeIfPresent(String.self, forKey: .characterAge)
        characterOccupation = try container.decodeIfPresent(String.self, forKey: .characterOccupation)
        characterAppearance = try container.decodeIfPresent(String.self, forKey: .characterAppearance)
        characterPersonality = try container.decodeIfPresent(String.self, forKey: .characterPersonality)
        characterBackground = try container.decodeIfPresent(String.self, forKey: .characterBackground)
        publicInfo = try container.decodeIfPresent(String.self, forKey: .publicInfo)
        portraitUrl = try container.decodeIfPresent(String.self, forKey: .portraitUrl)
        isHost = try container.decodeIfPresent(Bool.self, forKey: .isHost) ?? false
        isAI = try container.decodeIfPresent(Bool.self, forKey: .isAI) ?? false
        isReady = try container.decodeIfPresent(Bool.self, forKey: .isReady) ?? false
        connectionStatus = try container.decodeIfPresent(String.self, forKey: .connectionStatus) ?? "offline"
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

struct MyRoomItem: Codable, Identifiable, Sendable {
    var id: String { roomCode }
    let roomCode: String
    let status: String
    let isHost: Bool
    let displayName: String
    let characterName: String?
    let sessionToken: String
    let playerId: String
    let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case roomCode = "room_code"
        case status
        case isHost = "is_host"
        case displayName = "display_name"
        case characterName = "character_name"
        case sessionToken = "session_token"
        case playerId = "player_id"
        case createdAt = "created_at"
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

struct DebugInfoResponse: Codable, Sendable {
    let players: [DebugPlayerInfo]
}

struct DebugEvidenceInfo: Codable, Sendable {
    let title: String
    let content: String
    let source: String
}

struct DebugPlayerInfo: Codable, Identifiable, Sendable {
    let id: String
    let displayName: String
    let characterName: String?
    let role: String?
    let secretInfo: String?
    let objective: String?
    let isAI: Bool
    let evidences: [DebugEvidenceInfo]

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case characterName = "character_name"
        case role
        case secretInfo = "secret_info"
        case objective
        case isAI = "is_ai"
        case evidences
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        displayName = try container.decode(String.self, forKey: .displayName)
        characterName = try container.decodeIfPresent(String.self, forKey: .characterName)
        role = try container.decodeIfPresent(String.self, forKey: .role)
        secretInfo = try container.decodeIfPresent(String.self, forKey: .secretInfo)
        objective = try container.decodeIfPresent(String.self, forKey: .objective)
        isAI = try container.decodeIfPresent(Bool.self, forKey: .isAI) ?? false
        evidences = (try? container.decodeIfPresent([DebugEvidenceInfo].self, forKey: .evidences)) ?? []
    }
}

struct RoomInfoResponse: Codable, Sendable {
    let roomCode: String
    let status: String
    let players: [PlayerInfo]
    let hostPlayerId: String?
    let turnCount: Int?

    enum CodingKeys: String, CodingKey {
        case roomCode = "room_code"
        case status
        case players
        case hostPlayerId = "host_player_id"
        case turnCount = "turn_count"
    }
}
