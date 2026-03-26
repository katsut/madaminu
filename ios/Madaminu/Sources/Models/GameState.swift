import Foundation

struct PhaseInfo: Codable, Sendable {
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

struct InvestigationLocation: Codable, Identifiable, Sendable {
    let id: String
    let name: String
    let description: String
}

struct EvidenceItem: Codable, Identifiable, Sendable {
    let id = UUID()
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

struct ScenarioSettingData {
    var location: String?
    var situation: String?
    var victimName: String?
    var victimDescription: String?
    var sceneImageUrl: String?
}
