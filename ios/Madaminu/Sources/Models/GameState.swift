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
    let criminalEpilogue: String?
    let trueCriminalId: String
    let objectiveResults: [String: ObjectiveResult]?
    let voteDetails: [VoteDetail]?
    let voteCounts: [String: Int]?
    let arrestedName: String?
    let rankings: [PlayerRanking]?
    let characterReveals: [CharacterReveal]?

    enum CodingKeys: String, CodingKey {
        case endingText = "ending_text"
        case criminalEpilogue = "criminal_epilogue"
        case trueCriminalId = "true_criminal_id"
        case objectiveResults = "objective_results"
        case voteDetails = "vote_details"
        case voteCounts = "vote_counts"
        case arrestedName = "arrested_name"
        case rankings
        case characterReveals = "character_reveals"
    }
}

struct ObjectiveResult: Codable, Sendable {
    let achieved: Bool
    let description: String
}

struct VoteDetail: Codable, Sendable {
    let voter: String
    let suspect: String
}

struct PlayerRanking: Codable, Identifiable, Sendable {
    var id: String { playerId }
    let playerId: String
    let characterName: String
    let speechCount: Int
    let evidenceCount: Int
    let score: Int

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case characterName = "character_name"
        case speechCount = "speech_count"
        case evidenceCount = "evidence_count"
        case score
    }
}

struct CharacterReveal: Codable, Identifiable, Sendable {
    var id: String { playerId }
    let playerId: String
    let characterName: String
    let role: String?
    let secretInfo: String?
    let objective: String?

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case characterName = "character_name"
        case role
        case secretInfo = "secret_info"
        case objective
    }
}

struct DiscoveryItem: Identifiable, Sendable {
    let id: String
    let title: String
    var content: String
    var feature: String = ""
    var canTamper: Bool
    var isTampered: Bool = false
}

struct SpeechEntry: Identifiable, Sendable {
    let id = UUID()
    let playerId: String?
    let characterName: String
    let transcript: String
    let timestamp: Date = Date()
}

struct RevealedEvidence: Identifiable, Sendable {
    let id = UUID()
    let playerId: String?
    let playerName: String
    let title: String
    let content: String
    let timestamp: Date = Date()
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
    var gatheringReason: String?
    var murderDiscovery: String?
    var openingNarrative: String?
    var victimName: String?
    var victimDescription: String?
    var victimGreeting: String?
    var sceneImageUrl: String?
    var victimImageUrl: String?
    var mapUrl: String?
}
