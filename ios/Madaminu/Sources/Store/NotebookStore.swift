import Combine
import Foundation

final class NotebookStore: ObservableObject, @unchecked Sendable {
    @Published var evidences: [EvidenceItem] = []
    @Published var discussionLogs: [DiscussionLogEntry] = []
    @Published var notes = ""
    @Published var playerNotes: [String: String] = [:]  // playerId -> note

    func addDiscussionLog(turnNumber: Int, speeches: [SpeechEntry], reveals: [RevealedEvidence]) {
        if speeches.isEmpty && reveals.isEmpty { return }
        discussionLogs.append(DiscussionLogEntry(
            turnNumber: turnNumber,
            speeches: speeches,
            reveals: reveals
        ))
    }

    func reset() {
        evidences = []
        discussionLogs = []
        notes = ""
        playerNotes = [:]
    }
}

struct DiscussionLogEntry: Identifiable, Sendable {
    let id = UUID()
    let turnNumber: Int
    let speeches: [SpeechEntry]
    let reveals: [RevealedEvidence]
}
