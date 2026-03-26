import Combine
import Foundation

/// Central state machine managing the entire game lifecycle.
/// Single source of truth for all game state and screen transitions.
final class GameStore: ObservableObject, @unchecked Sendable {

    // MARK: - State Machine

    enum Screen: Equatable {
        case home
        case lobby
        case characterCreation
        case generating
        case intro
        case playing
        case ended
    }

    @Published var screen: Screen = .home
    @Published var errorMessage: String?

    // MARK: - User

    var displayName: String = "" {
        didSet { UserDefaults.standard.set(displayName, forKey: "displayName") }
    }

    // MARK: - Room State

    @Published var roomCode = ""
    @Published var players: [PlayerInfo] = []
    @Published var isHost = false
    @Published var isLoading = false
    @Published var progressMessage: String?
    @Published var availableRooms: [RoomListItem] = []
    @Published var hasCreatedCharacter = false

    var playerId: String?
    var sessionToken: String?

    // MARK: - Game State

    @Published var scenarioSetting = ScenarioSettingData()
    @Published var mySecretInfo: String?
    @Published var myObjective: String?
    @Published var myRole: String?
    @Published var currentPhase: PhaseInfo?
    @Published var currentSpeakerId: String?
    @Published var evidences: [EvidenceItem] = []
    @Published var notes = ""
    @Published var ending: EndingData?
    @Published var isSpeaking = false
    @Published var currentTranscript = ""
    @Published var isConnected = false

    // MARK: - Services

    private let api = APIClient()
    private let ws = WebSocketClient()
    private var speechRecognizer: SpeechRecognizer?

    // MARK: - Init

    init() {
        self.displayName = UserDefaults.standard.string(forKey: "displayName") ?? ""
    }

    // MARK: - Room Actions

    @MainActor func createRoom(password: String? = nil) async {
        guard !displayName.isEmpty else {
            errorMessage = "名前を入力してください"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.createRoom(displayName: displayName, password: password)
            roomCode = response.roomCode
            playerId = response.playerId
            sessionToken = response.sessionToken
            isHost = true
            screen = .lobby
            await refreshRoom()
        } catch {
            errorMessage = "ルーム作成に失敗しました"
        }

        isLoading = false
    }

    @MainActor func joinRoom(roomCode: String, password: String? = nil) async {
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
            screen = .lobby
            await refreshRoom()
        } catch {
            errorMessage = "ルームに参加できませんでした"
        }

        isLoading = false
    }

    @MainActor func fetchRooms() async {
        do {
            availableRooms = try await api.listRooms()
        } catch {
            availableRooms = []
        }
    }

    @MainActor func refreshRoom() async {
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

    func showCharacterCreation() {
        screen = .characterCreation
    }

    func dismissCharacterCreation() {
        screen = .lobby
    }

    @MainActor func createCharacter(name: String, personality: String, background: String) async {
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
            screen = .lobby
            await refreshRoom()
        } catch {
            errorMessage = "キャラクター作成に失敗しました"
        }

        isLoading = false
    }

    @MainActor func startGame() async {
        guard let token = sessionToken else { return }

        isLoading = true
        errorMessage = nil
        progressMessage = "AIプレイヤーを準備中..."

        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            if self?.isLoading == true { self?.progressMessage = "シナリオを生成中..." }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 13) { [weak self] in
            if self?.isLoading == true { self?.progressMessage = "物語を組み立てています..." }
        }

        do {
            try await api.startGame(roomCode: roomCode, sessionToken: token)
            screen = .generating
            connectWebSocket()
        } catch let apiError as APIError {
            if case .requestFailed(let code, _) = apiError, code == 400 {
                // Game already started — join in progress
                screen = .generating
                connectWebSocket()
            } else {
                errorMessage = "ゲーム開始に失敗しました"
            }
        } catch {
            errorMessage = "ゲーム開始に失敗しました"
        }

        progressMessage = nil
        isLoading = false
    }

    func leaveRoom() {
        ws.disconnect()
        screen = .home
        roomCode = ""
        players = []
        playerId = nil
        sessionToken = nil
        isHost = false
        hasCreatedCharacter = false
        isLoading = false
        progressMessage = nil
        errorMessage = nil
        resetGameState()
    }

    // MARK: - Game Actions

    func requestSpeech() {
        ws.send(type: "speech.request")
    }

    func releaseSpeech() {
        ws.send(type: "speech.release", data: ["transcript": currentTranscript])
        speechRecognizer?.stopRecording()
        isSpeaking = false
        currentTranscript = ""
    }

    func investigate(locationId: String) {
        ws.send(type: "investigate", data: ["location_id": locationId])
    }

    func vote(suspectPlayerId: String) {
        ws.send(type: "vote.submit", data: ["suspect_player_id": suspectPlayerId])
    }

    func advancePhase() {
        ws.send(type: "phase.advance")
    }

    func extendPhase() {
        ws.send(type: "phase.extend")
    }

    func dismissIntro() {
        screen = .playing
    }

    @MainActor func setupSpeech() async {
        let sr = SpeechRecognizer()
        speechRecognizer = sr
        await sr.requestPermission()
    }

    // MARK: - WebSocket

    private func connectWebSocket() {
        guard let token = sessionToken else { return }

        ws.setMessageHandler { [weak self] type, data in
            DispatchQueue.main.async {
                self?.handleMessage(type: type, data: data)
            }
        }
        ws.setStateChangeHandler { [weak self] connected, error in
            DispatchQueue.main.async {
                self?.isConnected = connected
                if let error { self?.errorMessage = error }
            }
        }
        ws.connect(roomCode: roomCode, token: token)
    }

    // MARK: - Message Handling

    private func handleMessage(type: String, data: [String: String]) {
        print("[GameStore] Received: \(type), screen=\(screen)")
        switch type {
        case "game.state":
            handleGameState(data)
        case "game.generating":
            if screen != .generating { screen = .generating }
        case "game.ready":
            screen = .intro
        case "phase.started":
            handlePhaseStarted(data)
        case "phase.timer":
            handlePhaseTimer(data)
        case "phase.ended":
            currentPhase = nil
        case "speech.granted":
            isSpeaking = true
            speechRecognizer?.startRecording { [weak self] transcript in
                DispatchQueue.main.async {
                    self?.currentTranscript = transcript
                }
            }
        case "speech.denied":
            setError("他のプレイヤーが発言中です")
        case "speech.active":
            currentSpeakerId = data["player_id"]
        case "speech.released":
            currentSpeakerId = nil
        case "investigate.result":
            let title = data["title"] ?? "調査結果"
            let content = data["content"] ?? ""
            evidences.append(EvidenceItem(title: title, content: content))
        case "investigate.denied":
            setError("調査できません")
        case "evidence.received":
            let title = data["title"] ?? "新しい手がかり"
            let content = data["content"] ?? ""
            evidences.append(EvidenceItem(title: title, content: content))
        case "game.ending":
            handleEnding(data)
        case "error":
            if let message = data["message"] {
                setError(message)
                if message.contains("Scenario") || message.contains("generation") || message.contains("failed") {
                    screen = .lobby
                    errorMessage = "シナリオ生成に失敗しました。もう一度お試しください。"
                }
            }
        default:
            break
        }
    }

    private func setError(_ message: String) {
        errorMessage = message
        DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak self] in
            if self?.errorMessage == message {
                self?.errorMessage = nil
            }
        }
    }

    private func handleGameState(_ data: [String: String]) {
        let status = data["status"] ?? ""

        mySecretInfo = data["my_secret_info"]
        myObjective = data["my_objective"]
        myRole = data["my_role"]
        currentSpeakerId = data["current_speaker_id"]

        if let settingJSON = data["scenario_setting"],
           let settingData = settingJSON.data(using: .utf8),
           let setting = try? JSONSerialization.jsonObject(with: settingData) as? [String: Any] {
            scenarioSetting.location = setting["location"] as? String
            scenarioSetting.situation = setting["situation"] as? String
        }

        scenarioSetting.sceneImageUrl = data["scene_image_url"]

        if let victimJSON = data["victim"],
           let victimData = victimJSON.data(using: .utf8),
           let victim = try? JSONSerialization.jsonObject(with: victimData) as? [String: Any] {
            scenarioSetting.victimName = victim["name"] as? String
            scenarioSetting.victimDescription = victim["description"] as? String
        }

        if let playersJSON = data["players"],
           let playersData = playersJSON.data(using: .utf8),
           let playersArray = try? JSONSerialization.jsonObject(with: playersData) as? [[String: Any]] {
            players = playersArray.compactMap { dict in
                guard let id = dict["id"] as? String,
                      let displayName = dict["display_name"] as? String else { return nil }
                return PlayerInfo(
                    id: id,
                    displayName: displayName,
                    characterName: dict["character_name"] as? String,
                    characterPersonality: dict["character_personality"] as? String,
                    characterBackground: dict["character_background"] as? String,
                    portraitUrl: dict["portrait_url"] as? String,
                    isHost: dict["is_host"] as? Bool ?? false,
                    isAI: dict["is_ai"] as? Bool ?? false,
                    connectionStatus: dict["connection_status"] as? String ?? "offline"
                )
            }
        }

        if let phaseJSON = data["current_phase"],
           let phaseData = phaseJSON.data(using: .utf8),
           let phaseDict = try? JSONSerialization.jsonObject(with: phaseData) as? [String: Any] {
            parsePhaseInfo(phaseDict)
        }

        // State transition based on server status
        if status == "playing" && (screen == .generating || screen == .lobby) {
            screen = .intro
        } else if status == "ended" {
            screen = .ended
        }
    }

    private func handlePhaseStarted(_ data: [String: String]) {
        parsePhaseInfo(stringDataToDict(data))
    }

    private func handlePhaseTimer(_ data: [String: String]) {
        guard let remainingStr = data["remaining_sec"], let remaining = Int(remainingStr) else { return }
        if let phase = currentPhase {
            currentPhase = PhaseInfo(
                phaseId: phase.phaseId,
                phaseType: phase.phaseType,
                phaseOrder: phase.phaseOrder,
                durationSec: phase.durationSec,
                remainingSec: remaining,
                investigationLocations: phase.investigationLocations
            )
        }
    }

    private func handleEnding(_ data: [String: String]) {
        let dict = stringDataToDict(data)
        guard let jsonData = try? JSONSerialization.data(withJSONObject: dict),
              let endingData = try? JSONDecoder().decode(EndingData.self, from: jsonData) else {
            setError("エンディングデータの解析に失敗しました")
            return
        }
        ending = endingData
        screen = .ended
    }

    // MARK: - Helpers

    private func resetGameState() {
        scenarioSetting = ScenarioSettingData()
        mySecretInfo = nil
        myObjective = nil
        myRole = nil
        currentPhase = nil
        currentSpeakerId = nil
        evidences = []
        notes = ""
        ending = nil
        isSpeaking = false
        currentTranscript = ""
        isConnected = false
        speechRecognizer = nil
    }

    private func parsePhaseInfo(_ data: [String: Any]) {
        guard let phaseId = data["phase_id"] as? String,
              let phaseType = data["phase_type"] as? String,
              let phaseOrder = data["phase_order"] as? Int,
              let durationSec = data["duration_sec"] as? Int else { return }

        var locations: [InvestigationLocation]?
        if let locsData = data["investigation_locations"] as? [[String: Any]] {
            locations = locsData.compactMap { loc in
                guard let id = loc["id"] as? String,
                      let name = loc["name"] as? String else { return nil }
                return InvestigationLocation(id: id, name: name, description: loc["description"] as? String ?? "")
            }
        }

        currentPhase = PhaseInfo(
            phaseId: phaseId,
            phaseType: phaseType,
            phaseOrder: phaseOrder,
            durationSec: durationSec,
            remainingSec: data["remaining_sec"] as? Int ?? durationSec,
            investigationLocations: locations
        )
    }

    private func stringDataToDict(_ data: [String: String]) -> [String: Any] {
        var result: [String: Any] = [:]
        for (key, value) in data {
            if let intVal = Int(value) {
                result[key] = intVal
            } else if let d = value.data(using: .utf8),
                      let json = try? JSONSerialization.jsonObject(with: d) {
                result[key] = json
            } else {
                result[key] = value
            }
        }
        return result
    }
}
