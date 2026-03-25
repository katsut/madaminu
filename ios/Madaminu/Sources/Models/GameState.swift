import Foundation

struct GameStateData: Codable {
    let roomCode: String
    let status: String
    let hostPlayerId: String?
    let players: [PlayerInfo]
    let mySecretInfo: String?
    let myObjective: String?
    let myRole: String?
    let currentPhase: PhaseInfo?
    let currentSpeakerId: String?

    enum CodingKeys: String, CodingKey {
        case roomCode = "room_code"
        case status
        case hostPlayerId = "host_player_id"
        case players
        case mySecretInfo = "my_secret_info"
        case myObjective = "my_objective"
        case myRole = "my_role"
        case currentPhase = "current_phase"
        case currentSpeakerId = "current_speaker_id"
    }
}

struct PhaseInfo: Codable {
    let phaseId: String
    let phaseType: String
    let phaseOrder: Int
    let durationSec: Int
    let remainingSec: Int
    let investigationLocations: [InvestigationLocation]?

    enum CodingKeys: String, CodingKey {
        case phaseId = "phase_id"
        case phaseType = "phase_type"
        case phaseOrder = "phase_order"
        case durationSec = "duration_sec"
        case remainingSec = "remaining_sec"
        case investigationLocations = "investigation_locations"
    }
}

struct InvestigationLocation: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
}

struct EvidenceItem: Codable, Identifiable {
    let id = UUID()
    let title: String
    let content: String

    enum CodingKeys: String, CodingKey {
        case title, content
    }
}

struct EndingData: Codable {
    let endingText: String
    let trueCriminalId: String
    let objectiveResults: [String: ObjectiveResult]?

    enum CodingKeys: String, CodingKey {
        case endingText = "ending_text"
        case trueCriminalId = "true_criminal_id"
        case objectiveResults = "objective_results"
    }
}

struct ObjectiveResult: Codable {
    let achieved: Bool
    let description: String
}

struct WSMessage: Codable {
    let type: String
    let data: [String: AnyCodable]?
}

struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let str = try? container.decode(String.self) {
            value = str
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else if let arr = try? container.decode([AnyCodable].self) {
            value = arr.map { $0.value }
        } else if container.decodeNil() {
            value = NSNull()
        } else {
            value = ""
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case let str as String: try container.encode(str)
        case let int as Int: try container.encode(int)
        case let double as Double: try container.encode(double)
        case let bool as Bool: try container.encode(bool)
        default: try container.encodeNil()
        }
    }

    var stringValue: String? { value as? String }
    var intValue: Int? { value as? Int }
    var dictValue: [String: Any]? { value as? [String: Any] }
}
