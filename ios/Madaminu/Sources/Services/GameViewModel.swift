import Foundation
import Observation

@MainActor
@Observable
final class GameViewModel {
    enum GameScreen { case intro, playing, ended }

    var screen: GameScreen = .intro
    var gameStatus = ""
    var currentPhase: PhaseInfo?
    var currentSpeakerId: String?
    var mySecretInfo: String?
    var myObjective: String?
    var myRole: String?
    var players: [PlayerInfo] = []
    var evidences: [EvidenceItem] = []
    var notes = ""
    var ending: EndingData?
    var isSpeaking = false
    var errorMessage: String?
    var isConnected = false
    var connectionError: String?
    var scenarioSetting: ScenarioSettingData = ScenarioSettingData()

    let roomCode: String
    let playerId: String
    let sessionToken: String
    let isHost: Bool

    private let ws = WebSocketClient()
    let speechRecognizer = SpeechRecognizer()

    init(roomCode: String, playerId: String, sessionToken: String, isHost: Bool) {
        self.roomCode = roomCode
        self.playerId = playerId
        self.sessionToken = sessionToken
        self.isHost = isHost
    }

    func connect() {
        ws.setMessageHandler { [weak self] type, data in
            Task { @MainActor [weak self] in
                self?.handleMessage(type: type, data: data)
            }
        }
        ws.setStateChangeHandler { [weak self] connected, error in
            Task { @MainActor [weak self] in
                self?.isConnected = connected
                self?.connectionError = error
            }
        }
        ws.connect(roomCode: roomCode, token: sessionToken)
    }

    func disconnect() {
        ws.disconnect()
    }

    func requestSpeech() {
        ws.send(type: "speech.request")
    }

    func releaseSpeech() {
        ws.send(type: "speech.release", data: [
            "transcript": speechRecognizer.transcript,
        ])
        speechRecognizer.stopRecording()
        isSpeaking = false
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

    private func setError(_ message: String) {
        errorMessage = message
        Task { @MainActor [weak self] in
            try? await Task.sleep(for: .seconds(5))
            if self?.errorMessage == message {
                self?.errorMessage = nil
            }
        }
    }

    private func handleMessage(type: String, data: [String: String]) {
        switch type {
        case "game.state":
            handleGameState(data)
        case "phase.started":
            handlePhaseStarted(data)
        case "phase.timer":
            handlePhaseTimer(data)
        case "phase.ended":
            currentPhase = nil
        case "speech.granted":
            isSpeaking = true
            speechRecognizer.startRecording()
        case "speech.denied":
            setError("他のプレイヤーが発言中です")
        case "speech.active":
            currentSpeakerId = data["player_id"]
        case "speech.released":
            currentSpeakerId = nil
        case "investigate.result":
            handleInvestigateResult(data)
        case "investigate.denied":
            setError("調査できません")
        case "evidence.received":
            handleEvidenceReceived(data)
        case "vote.results":
            break
        case "game.ending":
            handleEnding(data)
        case "error":
            if let message = data["message"] {
                setError(message)
            }
        default:
            break
        }
    }

    private func handleGameState(_ data: [String: String]) {
        gameStatus = data["status"] ?? ""
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
                    isHost: dict["is_host"] as? Bool ?? false,
                    connectionStatus: dict["connection_status"] as? String ?? "offline"
                )
            }
        }

        if let phaseJSON = data["current_phase"],
           let phaseData = phaseJSON.data(using: .utf8),
           let phaseDict = try? JSONSerialization.jsonObject(with: phaseData) as? [String: Any] {
            parsePhaseInfo(phaseDict)
        }
    }

    private func handlePhaseStarted(_ data: [String: String]) {
        let dict = stringDataToDict(data)
        parsePhaseInfo(dict)
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

    private func handleInvestigateResult(_ data: [String: String]) {
        let title = data["title"] ?? "調査結果"
        let content = data["content"] ?? ""
        evidences.append(EvidenceItem(title: title, content: content))
    }

    private func handleEvidenceReceived(_ data: [String: String]) {
        let title = data["title"] ?? "新しい手がかり"
        let content = data["content"] ?? ""
        evidences.append(EvidenceItem(title: title, content: content))
    }

    func dismissIntro() {
        screen = .playing
    }

    private func handleEnding(_ data: [String: String]) {
        let dict = stringDataToDict(data)
        guard let jsonData = try? JSONSerialization.data(withJSONObject: dict),
              let endingData = try? JSONDecoder().decode(EndingData.self, from: jsonData) else {
            setError("エンディングデータの解析に失敗しました")
            return
        }
        ending = endingData
        gameStatus = "ended"
        screen = .ended
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
                return InvestigationLocation(
                    id: id,
                    name: name,
                    description: loc["description"] as? String ?? ""
                )
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

struct ScenarioSettingData {
    var location: String?
    var situation: String?
    var victimName: String?
    var victimDescription: String?
}
