import Combine
import Foundation

final class AppStore: ObservableObject, @unchecked Sendable {
    @Published var screen: Screen = .home
    @Published var errorMessage: String?
    @Published var isLoading = false
    @Published var pendingJoinCode: String?

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
        case .createRoom(let roomName, let password):
            Task { @MainActor in await performCreateRoom(roomName: roomName, password: password) }
        case .joinRoom(let code, let password):
            Task { @MainActor in await performJoinRoom(code: code, password: password) }
        case .leaveRoom:
            performLeaveRoom()
        case .showCharacterCreation:
            screen = .characterCreation
        case .dismissCharacterCreation:
            screen = .lobby
        case .createCharacter(let name, let nameKana, let gender, let age, let occupation, let appearance, let personality, let background):
            Task { @MainActor in await performCreateCharacter(name: name, nameKana: nameKana, gender: gender, age: age, occupation: occupation, appearance: appearance, personality: personality, background: background) }
        case .toggleReady:
            Task { @MainActor in await performToggleReady() }
        case .startGame:
            Task { @MainActor in await performStartGame() }
        case .dismissIntro:
            ws.send(type: "intro.start_game")
            screen = .playing
        case .introReady:
            game.introReady = true
            ws.send(type: "intro.ready")
        case .introUnready:
            game.introReady = false
            ws.send(type: "intro.unready")
        case .requestSpeech:
            ws.send(type: "speech.request")
        case .releaseSpeech:
            ws.send(type: "speech.release", data: ["transcript": game.currentTranscript])
            speechRecognizer?.stopRecording()
            game.isSpeaking = false
            game.currentTranscript = ""
        case .investigate(let locationId):
            ws.send(type: "investigate", data: ["location_id": locationId])
        case .selectInvestigation(let locationId):
            game.selectedLocationId = locationId
            game.selectedFeature = nil
            ws.send(type: "investigate.select", data: ["location_id": locationId ?? ""])
        case .selectFeature(let feature):
            game.selectedFeature = feature
            if let locationId = game.selectedLocationId {
                ws.send(type: "investigate.select", data: ["location_id": locationId, "feature": feature])
            }
        case .keepEvidence(let discoveryId):
            ws.send(type: "investigate.keep", data: ["discovery_id": discoveryId])
        case .tamperEvidence(let discoveryId):
            ws.send(type: "investigate.tamper", data: ["discovery_id": discoveryId])
        case .revealEvidence(let evidenceId):
            ws.send(type: "evidence.reveal", data: ["evidence_id": evidenceId])
        case .sendRoomMessage(let text):
            ws.send(type: "room_message.send", data: ["text": text])
        case .vote(let suspectId):
            ws.send(type: "vote.submit", data: ["suspect_player_id": suspectId])
        case .advancePhase:
            ws.send(type: "phase.advance")
        case .extendPhase:
            ws.send(type: "phase.extend")
        case .pausePhase:
            ws.send(type: "phase.pause")
        case .resumePhase:
            ws.send(type: "phase.resume")
        case .fetchRooms:
            Task { @MainActor in await performFetchRooms() }
        case .fetchMyRooms:
            Task { @MainActor in await performFetchMyRooms() }
        case .deleteRoom(let roomCode):
            Task { @MainActor in await performDeleteRoom(roomCode: roomCode) }
        case .rejoinRoom(let sessionToken, let playerId, let roomCode, let status):
            room.sessionToken = sessionToken
            room.playerId = playerId
            room.roomCode = roomCode
            if status == "waiting" {
                screen = .lobby
                Task { @MainActor in await performRefreshRoom() }
            } else {
                // playing, generating, voting — connect WS, game.state will set screen
                connectWebSocket()
            }
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
                if connected {
                    self?.errorMessage = nil
                } else if let error {
                    self?.errorMessage = error
                }
            }
        }
        ws.connect(roomCode: room.roomCode, token: token)
    }

    func sendWS(type: String, data: [String: String] = [:]) {
        ws.send(type: type, data: data)
    }

    func reconnectWebSocket() {
        ws.disconnect()
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
            self?.connectWebSocket()
        }
    }

    // MARK: - Deep Link

    @MainActor func handleDeepLink(roomCode: String) {
        guard screen == .home else {
            errorMessage = "ゲーム中は参加できません"
            return
        }
        if room.displayName.isEmpty {
            // Show join dialog with pre-filled code
            pendingJoinCode = roomCode
            return
        }
        Task { await performJoinRoom(code: roomCode, password: nil) }
    }

    // MARK: - Private Actions

    @MainActor private func performCreateRoom(roomName: String?, password: String?) async {
        guard !room.displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.createRoom(displayName: room.displayName, roomName: roomName, password: password, turnCount: room.turnCount)
            room.roomCode = response.roomCode
            room.playerId = response.playerId
            room.sessionToken = response.sessionToken
            room.isHost = true
            screen = .lobby
            connectWebSocket()
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
            connectWebSocket()
            await performRefreshRoom()
        } catch {
            errorMessage = "ルームに参加できませんでした"
        }

        isLoading = false
    }

    @MainActor private func performToggleReady() async {
        guard let token = room.sessionToken else { return }
        do {
            try await api.toggleReady(roomCode: room.roomCode, sessionToken: token)
            await performRefreshRoom()
        } catch {
            errorMessage = "準備状態の変更に失敗しました"
        }
    }

    @MainActor private func performFetchRooms() async {
        do {
            room.availableRooms = try await api.listRooms()
        } catch {
            print("[AppStore] fetchRooms error: \(error)")
            room.availableRooms = []
        }
    }

    @MainActor private func performFetchMyRooms() async {
        do {
            room.myRooms = try await api.listMyRooms()
        } catch {
            room.myRooms = []
        }
    }

    @MainActor private func performDeleteRoom(roomCode: String) async {
        do {
            try await api.deleteRoom(roomCode: roomCode)
            room.myRooms.removeAll { $0.roomCode == roomCode }
        } catch {
            errorMessage = "ルームの削除に失敗しました"
        }
    }

    @MainActor private func performRefreshRoom() async {
        guard !room.roomCode.isEmpty else { return }

        do {
            let info = try await api.getRoomInfo(roomCode: room.roomCode)
            room.players = info.players
            if let turnCount = info.turnCount {
                room.turnCount = turnCount
            }

            if let me = room.players.first(where: { $0.id == room.playerId }) {
                room.hasCreatedCharacter = me.characterName != nil
                room.isHost = me.isHost
            }

            if info.status == "generating" || info.status == "playing" || info.status == "voting" {
                if screen == .lobby {
                    screen = .generating
                }
            }
        } catch {
            errorMessage = "ルーム情報の取得に失敗しました"
        }
    }

    @MainActor private func performCreateCharacter(name: String, nameKana: String, gender: String, age: String, occupation: String, appearance: String, personality: String, background: String) async {
        guard let token = room.sessionToken else { return }

        isLoading = true
        errorMessage = nil

        do {
            _ = try await api.createCharacter(
                roomCode: room.roomCode,
                sessionToken: token,
                name: name,
                nameKana: nameKana,
                gender: gender,
                age: age,
                occupation: occupation,
                appearance: appearance,
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

        screen = .generating
        errorMessage = nil

        do {
            try await api.startGame(roomCode: room.roomCode, sessionToken: token)
        } catch {
            errorMessage = "ゲーム開始に失敗しました"
            screen = .lobby
        }
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
