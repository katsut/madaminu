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
    var scenarioSetting: [String: Any] = [:]

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
            Task { @MainActor in
                self?.handleMessage(type: type, data: data)
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

    private func handleMessage(type: String, data: [String: Any]) {
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
            errorMessage = "他のプレイヤーが発言中です"
        case "speech.active":
            currentSpeakerId = data["player_id"] as? String
        case "speech.released":
            currentSpeakerId = nil
        case "investigate.result":
            handleInvestigateResult(data)
        case "investigate.denied":
            errorMessage = "調査できません"
        case "evidence.received":
            handleEvidenceReceived(data)
        case "vote.results":
            break
        case "game.ending":
            handleEnding(data)
        case "error":
            errorMessage = data["message"] as? String
        default:
            break
        }
    }

    private func handleGameState(_ data: [String: Any]) {
        gameStatus = data["status"] as? String ?? ""
        mySecretInfo = data["my_secret_info"] as? String
        myObjective = data["my_objective"] as? String

        if let setting = data["scenario_setting"] as? [String: Any] {
            scenarioSetting = setting
        }
        if let victim = data["victim"] as? [String: Any] {
            scenarioSetting["victim_name"] = victim["name"]
            scenarioSetting["victim_description"] = victim["description"]
        }
        myRole = data["my_role"] as? String
        currentSpeakerId = data["current_speaker_id"] as? String

        if let playersData = data["players"] as? [[String: Any]] {
            players = playersData.compactMap { dict in
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

        if let phaseData = data["current_phase"] as? [String: Any] {
            parsePhaseInfo(phaseData)
        }
    }

    private func handlePhaseStarted(_ data: [String: Any]) {
        parsePhaseInfo(data)
    }

    private func handlePhaseTimer(_ data: [String: Any]) {
        guard let remaining = data["remaining_sec"] as? Int else { return }
        if var phase = currentPhase {
            phase = PhaseInfo(
                phaseId: phase.phaseId,
                phaseType: phase.phaseType,
                phaseOrder: phase.phaseOrder,
                durationSec: phase.durationSec,
                remainingSec: remaining,
                investigationLocations: phase.investigationLocations
            )
            currentPhase = phase
        }
    }

    private func handleInvestigateResult(_ data: [String: Any]) {
        let title = data["title"] as? String ?? "調査結果"
        let content = data["content"] as? String ?? ""
        evidences.append(EvidenceItem(title: title, content: content))
    }

    private func handleEvidenceReceived(_ data: [String: Any]) {
        let title = data["title"] as? String ?? "新しい手がかり"
        let content = data["content"] as? String ?? ""
        evidences.append(EvidenceItem(title: title, content: content))
    }

    func dismissIntro() {
        screen = .playing
    }

    private func handleEnding(_ data: [String: Any]) {
        guard let jsonData = try? JSONSerialization.data(withJSONObject: data),
              let endingData = try? JSONDecoder().decode(EndingData.self, from: jsonData) else { return }
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
}
