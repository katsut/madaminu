import Foundation
import Observation

@MainActor
@Observable
final class RoomViewModel {
    var displayName: String {
        didSet { UserDefaults.standard.set(displayName, forKey: "displayName") }
    }

    var roomCode: String = "" {
        didSet { UserDefaults.standard.set(roomCode, forKey: "session.roomCode") }
    }

    var joinCode = ""
    var password = ""
    var availableRooms: [RoomListItem] = []
    var players: [PlayerInfo] = []

    var isHost: Bool = false {
        didSet { UserDefaults.standard.set(isHost, forKey: "session.isHost") }
    }

    var isLoading = false
    var errorMessage: String?

    var playerId: String? {
        didSet { UserDefaults.standard.set(playerId, forKey: "session.playerId") }
    }

    var sessionToken: String? {
        didSet { UserDefaults.standard.set(sessionToken, forKey: "session.sessionToken") }
    }

    var isInRoom: Bool = false {
        didSet { UserDefaults.standard.set(isInRoom, forKey: "session.isInRoom") }
    }

    var showCharacterCreation = false
    var hasCreatedCharacter = false

    var isGameStarted: Bool = false {
        didSet { UserDefaults.standard.set(isGameStarted, forKey: "session.isGameStarted") }
    }

    var progressMessage: String?

    private let api = APIClient()

    init() {
        let defaults = UserDefaults.standard
        self.displayName = defaults.string(forKey: "displayName") ?? ""
        self.playerId = defaults.string(forKey: "session.playerId")
        self.sessionToken = defaults.string(forKey: "session.sessionToken")
        self.roomCode = defaults.string(forKey: "session.roomCode") ?? ""
        self.isHost = defaults.bool(forKey: "session.isHost")
        self.isInRoom = defaults.bool(forKey: "session.isInRoom")
        self.isGameStarted = defaults.bool(forKey: "session.isGameStarted")
    }

    var canStartGame: Bool {
        isHost && players.count >= 4
    }

    var allPlayersReady: Bool {
        players.allSatisfy { $0.characterName != nil }
    }

    func clearSavedSession() {
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "session.playerId")
        defaults.removeObject(forKey: "session.sessionToken")
        defaults.removeObject(forKey: "session.roomCode")
        defaults.removeObject(forKey: "session.isHost")
        defaults.removeObject(forKey: "session.isInRoom")
        defaults.removeObject(forKey: "session.isGameStarted")
    }

    func createRoom() async {
        guard !displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.createRoom(displayName: displayName, password: password.isEmpty ? nil : password)
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
            let response = try await api.joinRoom(roomCode: joinCode, displayName: displayName, password: password.isEmpty ? nil : password)
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

    func fetchRooms() async {
        do {
            availableRooms = try await api.listRooms()
        } catch {
            availableRooms = []
        }
    }

    func joinFromList(roomCode: String, password: String? = nil) async {
        guard !displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.joinRoom(roomCode: roomCode, displayName: displayName, password: password)
            self.roomCode = roomCode
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
        clearSavedSession()
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
