import Foundation
import Observation

@MainActor
@Observable
final class RoomViewModel {
    var displayName: String {
        didSet { UserDefaults.standard.set(displayName, forKey: "displayName") }
    }

    var roomCode = ""
    var joinCode = ""
    var players: [PlayerInfo] = []
    var isHost = false
    var isLoading = false
    var errorMessage: String?
    var playerId: String?
    var sessionToken: String?
    var isInRoom = false
    var showCharacterCreation = false
    var hasCreatedCharacter = false
    var isGameStarted = false
    var progressMessage: String?

    private let api = APIClient()

    init() {
        self.displayName = UserDefaults.standard.string(forKey: "displayName") ?? ""
    }

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

    func leaveRoom() {
        isInRoom = false
        roomCode = ""
        players = []
        playerId = nil
        sessionToken = nil
        isHost = false
        hasCreatedCharacter = false
        isGameStarted = false
        errorMessage = nil
    }

    func refreshRoom() async {
        guard !roomCode.isEmpty else { return }

        do {
            let info = try await api.getRoomInfo(roomCode: roomCode)
            players = info.players

            if let me = players.first(where: { $0.id == playerId }) {
                hasCreatedCharacter = me.characterName != nil
            }
        } catch {
            errorMessage = "ルーム情報の取得に失敗しました"
        }
    }

    func startGame() async {
        guard let token = sessionToken else { return }

        isLoading = true
        errorMessage = nil
        progressMessage = "AIプレイヤーを準備中..."

        Task { @MainActor in
            try? await Task.sleep(for: .seconds(3))
            if isLoading { progressMessage = "シナリオを生成中..." }
            try? await Task.sleep(for: .seconds(10))
            if isLoading { progressMessage = "物語を組み立てています..." }
            try? await Task.sleep(for: .seconds(15))
            if isLoading { progressMessage = "もう少しお待ちください..." }
        }

        do {
            try await api.startGame(roomCode: roomCode, sessionToken: token)
            progressMessage = nil
            isGameStarted = true
        } catch let apiError as APIError {
            switch apiError {
            case .requestFailed(let code, let msg):
                errorMessage = "ゲーム開始に失敗しました (\(code)): \(msg)"
            default:
                errorMessage = "ゲーム開始に失敗しました: \(apiError)"
            }
        } catch {
            errorMessage = "ゲーム開始に失敗しました: \(error.localizedDescription)"
        }

        progressMessage = nil
        isLoading = false
    }

    func createCharacter(name: String, personality: String, background: String) async {
        guard let token = sessionToken else { return }

        isLoading = true
        errorMessage = nil

        do {
            _ = try await api.createCharacter(
                roomCode: roomCode,
                sessionToken: token,
                name: name,
                personality: personality,
                background: background
            )
            hasCreatedCharacter = true
            showCharacterCreation = false
            await refreshRoom()
        } catch {
            errorMessage = "キャラクター作成に失敗しました"
        }

        isLoading = false
    }
}
