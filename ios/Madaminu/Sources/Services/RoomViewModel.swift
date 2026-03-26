import Combine
import Foundation

final class RoomViewModel: ObservableObject, @unchecked Sendable {
    // MARK: - User input (persisted)
    @Published var displayName: String = "" {
        didSet { UserDefaults.standard.set(displayName, forKey: "displayName") }
    }

    // MARK: - Room state
    @Published var roomCode = ""
    @Published var joinCode = ""
    @Published var password = ""
    @Published var availableRooms: [RoomListItem] = []
    @Published var players: [PlayerInfo] = []
    @Published var isHost = false
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var playerId: String?
    @Published var sessionToken: String?
    @Published var isInRoom = false
    @Published var showCharacterCreation = false
    @Published var hasCreatedCharacter = false
    @Published var isGameStarted = false
    @Published var progressMessage: String?

    private let api = APIClient()

    init() {
        self.displayName = UserDefaults.standard.string(forKey: "displayName") ?? ""
    }

    var allPlayersReady: Bool {
        players.allSatisfy { $0.characterName != nil }
    }

    // MARK: - Room actions

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

        Task { [weak self] in
            try? await Task.sleep(for: .seconds(3))
            if self?.isLoading == true { self?.progressMessage = "シナリオを生成中..." }
            try? await Task.sleep(for: .seconds(10))
            if self?.isLoading == true { self?.progressMessage = "物語を組み立てています..." }
            try? await Task.sleep(for: .seconds(15))
            if self?.isLoading == true { self?.progressMessage = "もう少しお待ちください..." }
        }

        do {
            try await api.startGame(roomCode: roomCode, sessionToken: token)
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
