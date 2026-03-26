import Combine
import Foundation

final class AppStore: ObservableObject, @unchecked Sendable {
    @Published var screen: Screen = .home
    @Published var errorMessage: String?
    @Published var isLoading = false

    let room = RoomStore()
    let game = GamePlayStore()
    let notebook = NotebookStore()

    private let api = APIClient()
    private let ws = WebSocketClient()
    private var speechRecognizer: SpeechRecognizer?
    private var cancellables = Set<AnyCancellable>()

    init() {
        room.objectWillChange.sink { [weak self] in self?.objectWillChange.send() }.store(in: &cancellables)
        game.objectWillChange.sink { [weak self] in self?.objectWillChange.send() }.store(in: &cancellables)
        notebook.objectWillChange.sink { [weak self] in self?.objectWillChange.send() }.store(in: &cancellables)
    }

    // MARK: - Actions

    func dispatch(_ action: AppAction) {
        switch action {
        case .createRoom(let password):
            Task { @MainActor in await performCreateRoom(password: password) }
        case .joinRoom(let code, let password):
            Task { @MainActor in await performJoinRoom(code: code, password: password) }
        case .leaveRoom:
            performLeaveRoom()
        case .showCharacterCreation:
            screen = .characterCreation
        case .dismissCharacterCreation:
            screen = .lobby
        case .createCharacter(let name, let personality, let background):
            Task { @MainActor in await performCreateCharacter(name: name, personality: personality, background: background) }
        case .startGame:
            Task { @MainActor in await performStartGame() }
        case .dismissIntro:
            screen = .playing
        case .requestSpeech:
            ws.send(type: "speech.request")
        case .releaseSpeech:
            ws.send(type: "speech.release", data: ["transcript": game.currentTranscript])
            speechRecognizer?.stopRecording()
            game.isSpeaking = false
            game.currentTranscript = ""
        case .investigate(let locationId):
            ws.send(type: "investigate", data: ["location_id": locationId])
        case .vote(let suspectId):
            ws.send(type: "vote.submit", data: ["suspect_player_id": suspectId])
        case .advancePhase:
            ws.send(type: "phase.advance")
        case .extendPhase:
            ws.send(type: "phase.extend")
        case .fetchRooms:
            Task { @MainActor in await performFetchRooms() }
        case .refreshRoom:
            Task { @MainActor in await performRefreshRoom() }
        }
    }

    // MARK: - Error Handling

    func setError(_ message: String, level: ErrorLevel) {
        DispatchQueue.main.async { [weak self] in
            self?.errorMessage = message
            switch level {
            case .transient:
                DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak self] in
                    if self?.errorMessage == message { self?.errorMessage = nil }
                }
            case .recoverable:
                break
            case .fatal:
                self?.screen = .lobby
            }
        }
    }

    // MARK: - Speech

    @MainActor func setupSpeech() async {
        let sr = SpeechRecognizer()
        speechRecognizer = sr
        await sr.requestPermission()
    }

    func startRecording() {
        speechRecognizer?.startRecording { [weak self] transcript in
            DispatchQueue.main.async {
                self?.game.currentTranscript = transcript
            }
        }
    }

    // MARK: - WebSocket

    func connectWebSocket() {
        guard let token = room.sessionToken else {
            print("[AppStore] connectWebSocket: no token")
            return
        }

        print("[AppStore] connectWebSocket: room=\(room.roomCode)")

        ws.setMessageHandler { [weak self] type, data in
            DispatchQueue.main.async {
                guard let self else { return }
                print("[AppStore] WS message: \(type)")
                WSMessageAdapter.apply(type: type, data: data, store: self)
            }
        }
        ws.setStateChangeHandler { [weak self] connected, error in
            DispatchQueue.main.async {
                print("[AppStore] WS state: connected=\(connected) error=\(error ?? "nil")")
                self?.game.isConnected = connected
                if let error { self?.errorMessage = error }
            }
        }
        ws.connect(roomCode: room.roomCode, token: token)
    }

    func reconnectWebSocket() {
        ws.disconnect()
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
            self?.connectWebSocket()
        }
    }

    // MARK: - Private Actions

    @MainActor private func performCreateRoom(password: String?) async {
        guard !room.displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.createRoom(displayName: room.displayName, password: password)
            room.roomCode = response.roomCode
            room.playerId = response.playerId
            room.sessionToken = response.sessionToken
            room.isHost = true
            screen = .lobby
            await performRefreshRoom()
        } catch {
            errorMessage = "ルーム作成に失敗しました"
        }

        isLoading = false
    }

    @MainActor private func performJoinRoom(code: String, password: String?) async {
        guard !room.displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.joinRoom(roomCode: code, displayName: room.displayName, password: password)
            room.roomCode = code
            room.playerId = response.playerId
            room.sessionToken = response.sessionToken
            room.isHost = false
            screen = .lobby
            await performRefreshRoom()
        } catch {
            errorMessage = "ルームに参加できませんでした"
        }

        isLoading = false
    }

    @MainActor private func performFetchRooms() async {
        do {
            room.availableRooms = try await api.listRooms()
        } catch {
            room.availableRooms = []
        }
    }

    @MainActor private func performRefreshRoom() async {
        guard !room.roomCode.isEmpty else { return }

        do {
            let info = try await api.getRoomInfo(roomCode: room.roomCode)
            room.players = info.players

            if let me = room.players.first(where: { $0.id == room.playerId }) {
                room.hasCreatedCharacter = me.characterName != nil
            }
        } catch {
            errorMessage = "ルーム情報の取得に失敗しました"
        }
    }

    @MainActor private func performCreateCharacter(name: String, personality: String, background: String) async {
        guard let token = room.sessionToken else { return }

        isLoading = true
        errorMessage = nil

        do {
            _ = try await api.createCharacter(
                roomCode: room.roomCode,
                sessionToken: token,
                name: name,
                personality: personality,
                background: background
            )
            room.hasCreatedCharacter = true
            screen = .lobby
            await performRefreshRoom()
        } catch {
            errorMessage = "キャラクター作成に失敗しました"
        }

        isLoading = false
    }

    @MainActor private func performStartGame() async {
        guard let token = room.sessionToken else { return }

        isLoading = true
        errorMessage = nil
        room.progressMessage = "AIプレイヤーを準備中..."

        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            if self?.isLoading == true { self?.room.progressMessage = "シナリオを生成中..." }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 8) { [weak self] in
            if self?.isLoading == true { self?.room.progressMessage = "キャラクターを生成中..." }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 15) { [weak self] in
            if self?.isLoading == true { self?.room.progressMessage = "イラストを生成中..." }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 25) { [weak self] in
            if self?.isLoading == true { self?.room.progressMessage = "物語を組み立てています..." }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 40) { [weak self] in
            if self?.isLoading == true { self?.room.progressMessage = "もう少しお待ちください..." }
        }

        do {
            try await api.startGame(roomCode: room.roomCode, sessionToken: token)
            screen = .generating
            connectWebSocket()
        } catch let apiError as APIError {
            if case .requestFailed(let code, _) = apiError, code == 400 {
                screen = .generating
                connectWebSocket()
            } else {
                errorMessage = "ゲーム開始に失敗しました"
            }
        } catch {
            errorMessage = "ゲーム開始に失敗しました"
        }

        room.progressMessage = nil
        isLoading = false
    }

    private func performLeaveRoom() {
        ws.disconnect()
        screen = .home
        room.reset()
        game.reset()
        notebook.reset()
        isLoading = false
        errorMessage = nil
        speechRecognizer = nil
    }
}
