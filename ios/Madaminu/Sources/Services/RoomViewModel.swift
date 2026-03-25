import Foundation
import Observation

@MainActor
@Observable
final class RoomViewModel {
    var displayName = ""
    var roomCode = ""
    var joinCode = ""
    var players: [PlayerInfo] = []
    var isHost = false
    var isLoading = false
    var errorMessage: String?
    var playerId: String?
    var sessionToken: String?
    var isInRoom = false

    private let api = APIClient()

    var canStartGame: Bool {
        isHost && players.count >= 4
    }

    var allPlayersReady: Bool {
        players.allSatisfy { $0.characterName != nil }
    }

    func createRoom() async {
        guard !displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.createRoom(displayName: displayName)
            roomCode = response.roomCode
            playerId = response.playerId
            sessionToken = response.sessionToken
            isHost = true
            isInRoom = true
            await refreshRoom()
        } catch {
            errorMessage = "ルーム作成に失敗しました"
        }

        isLoading = false
    }

    func joinRoom() async {
        guard !displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }
        guard !joinCode.isEmpty else {
            errorMessage = "参加コードを入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.joinRoom(roomCode: joinCode, displayName: displayName)
            roomCode = joinCode
            playerId = response.playerId
            sessionToken = response.sessionToken
            isHost = false
            isInRoom = true
            await refreshRoom()
        } catch {
            errorMessage = "ルームに参加できませんでした"
        }

        isLoading = false
    }

    func refreshRoom() async {
        guard !roomCode.isEmpty else { return }

        do {
            let info = try await api.getRoomInfo(roomCode: roomCode)
            players = info.players
        } catch {
            errorMessage = "ルーム情報の取得に失敗しました"
        }
    }
}
