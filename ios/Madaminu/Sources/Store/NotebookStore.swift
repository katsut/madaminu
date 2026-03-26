import Combine
import Foundation

final class NotebookStore: ObservableObject, @unchecked Sendable {
    @Published var evidences: [EvidenceItem] = []
    @Published var notes = ""

    func reset() {
        evidences = []
        notes = ""
    }
}
