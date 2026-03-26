import Combine
import Foundation

final class RoomStore: ObservableObject, @unchecked Sendable {
    var displayName: String = "" {
        didSet { UserDefaults.standard.set(displayName, forKey: "displayName") }
    }
    @Published var roomCode = ""
    @Published var players: [PlayerInfo] = []
    @Published var isHost = false
    @Published var hasCreatedCharacter = false
    @Published var availableRooms: [RoomListItem] = []
    @Published var progressMessage: String?

    var playerId: String?
    var sessionToken: String?

    init() {
        displayName = UserDefaults.standard.string(forKey: "displayName") ?? ""
    }

    func reset() {
        roomCode = ""
        players = []
        isHost = false
        hasCreatedCharacter = false
        playerId = nil
        sessionToken = nil
        progressMessage = nil
    }
}
