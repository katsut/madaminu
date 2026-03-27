import Foundation

struct PhaseInfo: Codable, Sendable {
    let phaseId: String
    let phaseType: String
    let phaseOrder: Int
    let totalPhases: Int
    let durationSec: Int
    let remainingSec: Int
    let turnNumber: Int
    let totalTurns: Int
    let investigationLocations: [InvestigationLocation]?

    enum CodingKeys: String, CodingKey {
        case phaseId = "phase_id"
        case phaseType = "phase_type"
        case phaseOrder = "phase_order"
        case totalPhases = "total_phases"
        case durationSec = "duration_sec"
        case remainingSec = "remaining_sec"
        case turnNumber = "turn_number"
        case totalTurns = "total_turns"
        case investigationLocations = "investigation_locations"
    }
}

struct InvestigationLocation: Codable, Identifiable, Sendable {
    let id: String
    let name: String
    let description: String
    let features: [String]?
}

struct EvidenceItem: Codable, Identifiable, Sendable {
    let id = UUID()
    var evidenceId: String?
    let title: String
    let content: String

    enum CodingKeys: String, CodingKey {
        case title, content
    }
}

struct EndingData: Codable, Sendable {
    let endingText: String
    let trueCriminalId: String
    let objectiveResults: [String: ObjectiveResult]?

    enum CodingKeys: String, CodingKey {
        case endingText = "ending_text"
        case trueCriminalId = "true_criminal_id"
        case objectiveResults = "objective_results"
    }
}

struct ObjectiveResult: Codable, Sendable {
    let achieved: Bool
    let description: String
}

struct DiscoveryItem: Identifiable, Sendable {
    let id: String
    let title: String
    var content: String
    var canTamper: Bool
    var isTampered: Bool = false
}

struct RevealedEvidence: Identifiable, Sendable {
    let id = UUID()
    let playerName: String
    let title: String
    let content: String
}

struct ColocatedPlayer: Identifiable, Sendable {
    let id: String
    let characterName: String
    let portraitUrl: String?
}

struct RoomMessage: Identifiable, Sendable {
    let id = UUID()
    let senderId: String
    let senderName: String
    let text: String
}

struct ScenarioSettingData {
    var location: String?
    var situation: String?
    var victimName: String?
    var victimDescription: String?
    var sceneImageUrl: String?
    var victimImageUrl: String?
    var mapUrl: String?
}
