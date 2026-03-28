import Foundation

struct WSMessageAdapter {
    static func apply(type: String, data: [String: String], store: AppStore) {
        print("[WSMessageAdapter] Received: \(type), screen=\(store.screen)")
        switch type {
        case "game.state":
            applyGameState(data, store: store)
        case "game.generating":
            store.game.aiPlayersReady = true
            if store.screen != .generating { store.screen = .generating }
        case "progress":
            let step = data["step"] ?? ""
            let status = data["status"] ?? ""
            if step == "scenario" && status == "done" {
                store.game.scenarioReady = true
            } else if step == "scene_image" && status == "done" {
                store.game.sceneImageReady = true
            } else if step == "portraits" && status == "done" {
                store.game.portraitsReady = true
            }
        case "game.ready":
            store.game.allReady = true
            if store.screen == .generating {
                store.screen = store.game.scenarioSetting.sceneImageUrl != nil ? .intro : .playing
            }
        case "phase.started":
            applyPhaseStarted(data, store: store)
        case "phase.timer":
            applyPhaseTimer(data, store: store)
        case "phase.paused":
            store.game.isPaused = true
        case "phase.resumed":
            store.game.isPaused = false
            if let remainingStr = data["remaining_sec"], let remaining = Int(remainingStr) {
                store.game.localRemainingSec = remaining
            }
        case "phase.ended":
            if let nextType = data["next_phase_type"], !nextType.isEmpty {
                store.game.showPhaseTransition = true
                store.game.nextPhaseType = nextType
            }
            store.game.currentPhase = nil
        case "speech.granted":
            store.game.isSpeaking = true
            store.startRecording()
        case "speech.denied":
            store.setError("他のプレイヤーが発言中です", level: .transient)
        case "speech.active":
            store.game.currentSpeakerId = data["player_id"]
        case "speech.released", "speech.ai":
            if type == "speech.released" {
                store.game.currentSpeakerId = nil
            }
            let characterName = data["character_name"] ?? ""
            let transcript = data["transcript"] ?? ""
            if !transcript.isEmpty {
                store.game.speechHistory.append(SpeechEntry(characterName: characterName, transcript: transcript))
            }
        case "investigate.discoveries":
            print("[WSMessageAdapter] discoveries raw keys: \(data.keys.sorted())")
            print("[WSMessageAdapter] discoveries value: \(data["discoveries"]?.prefix(200) ?? "nil")")
            if let discJSON = data["discoveries"],
               let discData = discJSON.data(using: .utf8),
               let discArray = try? JSONSerialization.jsonObject(with: discData) as? [[String: Any]] {
                print("[WSMessageAdapter] parsed \(discArray.count) discoveries")
                store.game.discoveries = discArray.compactMap { d in
                    guard let id = d["id"] as? String,
                          let title = d["title"] as? String,
                          let content = d["content"] as? String else {
                        print("[WSMessageAdapter] discovery parse failed: \(d.keys)")
                        return nil
                    }
                    let canTamper = d["can_tamper"] as? Bool ?? false
                    return DiscoveryItem(id: id, title: title, content: content, canTamper: canTamper)
                }
                print("[WSMessageAdapter] final discoveries count: \(store.game.discoveries.count)")
            }
        case "investigate.discovery":
            let id = data["id"] ?? UUID().uuidString
            let title = data["title"] ?? "調査結果"
            let content = data["content"] ?? ""
            let canTamper = data["can_tamper"] == "1" || data["can_tamper"] == "true"
            store.game.discoveries.append(DiscoveryItem(id: id, title: title, content: content, canTamper: canTamper))
        case "investigate.kept":
            let title = data["title"] ?? "調査結果"
            let content = data["content"] ?? ""
            store.notebook.evidences.append(EvidenceItem(title: title, content: content))
            if let id = data["id"] { store.game.keptDiscoveryId = id }
        case "investigate.tampered":
            if let id = data["id"] {
                if let idx = store.game.discoveries.firstIndex(where: { $0.id == id }) {
                    store.game.discoveries[idx].content = data["content"] ?? store.game.discoveries[idx].content
                    store.game.discoveries[idx].isTampered = true
                }
            }
        case "investigate.result":
            let title = data["title"] ?? "調査結果"
            let content = data["content"] ?? ""
            store.notebook.evidences.append(EvidenceItem(title: title, content: content))
        case "investigate.denied":
            store.setError("調査できません", level: .transient)
        case "evidence.received":
            let title = data["title"] ?? "新しい手がかり"
            let content = data["content"] ?? ""
            var item = EvidenceItem(title: title, content: content)
            item.evidenceId = data["evidence_id"]
            store.notebook.evidences.append(item)
        case "location.colocated":
            if let playersJSON = data["players"],
               let playersData = playersJSON.data(using: .utf8),
               let playersArray = try? JSONSerialization.jsonObject(with: playersData) as? [[String: Any]] {
                store.game.colocatedPlayers = playersArray.compactMap { dict in
                    guard let id = dict["player_id"] as? String,
                          let name = dict["character_name"] as? String else { return nil }
                    return ColocatedPlayer(id: id, characterName: name, portraitUrl: dict["portrait_url"] as? String)
                }
            } else {
                store.game.colocatedPlayers = []
            }
        case "room_message.received":
            let senderId = data["sender_id"] ?? ""
            let senderName = data["sender_name"] ?? ""
            let text = data["text"] ?? ""
            store.game.roomMessages.append(RoomMessage(senderId: senderId, senderName: senderName, text: text))
        case "evidence.revealed":
            let playerId = data["player_id"] ?? ""
            let playerName = data["player_name"] ?? "不明"
            let title = data["title"] ?? ""
            let content = data["content"] ?? ""
            store.game.revealedEvidences.insert(
                RevealedEvidence(playerName: playerName, title: title, content: content),
                at: 0
            )
            if playerId != store.room.playerId {
                store.notebook.evidences.append(EvidenceItem(title: "[\(playerName)] \(title)", content: content))
            }
        case "intro.ready.count":
            if let countStr = data["count"], let count = Int(countStr) {
                store.game.introReadyCount = count
            }
        case "intro.start_game":
            if store.screen == .intro {
                store.screen = .playing
            }
        case "game.generation_failed":
            store.setError("シナリオ生成に失敗しました。もう一度お試しください。", level: .transient)
            store.game.reset()
            store.screen = .lobby
        case "game.ending":
            applyEnding(data, store: store)
        case "error":
            if let msg = data["message"] {
                store.setError(msg, level: .transient)
            }
        default:
            break
        }
    }

    // MARK: - Private Helpers

    private static func applyGameState(_ data: [String: String], store: AppStore) {
        let status = data["status"] ?? ""
        print("[WSMessageAdapter] applyGameState: status=\(status), keys=\(data.keys.sorted())")
        print("[WSMessageAdapter] mySecretInfo=\(data["my_secret_info"] ?? "nil"), myObjective=\(data["my_objective"] ?? "nil"), myRole=\(data["my_role"] ?? "nil")")

        if let secret = data["my_secret_info"] {
            store.game.mySecretInfo = secret
        }
        if let objective = data["my_objective"] {
            store.game.myObjective = objective
        }
        if let role = data["my_role"] {
            store.game.myRole = role
        }
        store.game.currentSpeakerId = data["current_speaker_id"]

        if let settingJSON = data["scenario_setting"],
           let settingData = settingJSON.data(using: .utf8),
           let setting = try? JSONSerialization.jsonObject(with: settingData) as? [String: Any] {
            store.game.scenarioSetting.location = setting["location"] as? String
            store.game.scenarioSetting.situation = setting["situation"] as? String
        }

        if let sceneUrl = data["scene_image_url"] {
            store.game.scenarioSetting.sceneImageUrl = sceneUrl
        }
        if let victimUrl = data["victim_image_url"] {
            store.game.scenarioSetting.victimImageUrl = victimUrl
        }
        if let mapUrl = data["map_url"] {
            store.game.scenarioSetting.mapUrl = mapUrl
        }

        if let victimJSON = data["victim"],
           let victimData = victimJSON.data(using: .utf8),
           let victim = try? JSONSerialization.jsonObject(with: victimData) as? [String: Any] {
            store.game.scenarioSetting.victimName = victim["name"] as? String
            store.game.scenarioSetting.victimDescription = victim["description"] as? String
        }

        if let playersJSON = data["players"],
           let playersData = playersJSON.data(using: .utf8),
           let playersArray = try? JSONSerialization.jsonObject(with: playersData) as? [[String: Any]] {
            store.room.players = playersArray.compactMap { dict in
                guard let id = dict["id"] as? String,
                      let displayName = dict["display_name"] as? String else { return nil }
                return PlayerInfo(
                    id: id,
                    displayName: displayName,
                    characterName: dict["character_name"] as? String,
                    characterNameKana: dict["character_name_kana"] as? String,
                    characterGender: dict["character_gender"] as? String,
                    characterAge: dict["character_age"] as? String,
                    characterOccupation: dict["character_occupation"] as? String,
                    characterAppearance: dict["character_appearance"] as? String,
                    characterPersonality: dict["character_personality"] as? String,
                    characterBackground: dict["character_background"] as? String,
                    publicInfo: dict["public_info"] as? String,
                    portraitUrl: dict["portrait_url"] as? String,
                    isHost: dict["is_host"] as? Bool ?? false,
                    isAI: dict["is_ai"] as? Bool ?? false,
                    connectionStatus: dict["connection_status"] as? String ?? "offline"
                )
            }

            if let hostId = data["host_player_id"] {
                store.room.isHost = (hostId == store.room.playerId)
            }
        }

        if let evJSON = data["my_evidences"],
           let evData = evJSON.data(using: .utf8),
           let evArray = try? JSONSerialization.jsonObject(with: evData) as? [[String: Any]] {
            store.notebook.evidences = evArray.compactMap { dict in
                guard let title = dict["title"] as? String,
                      let content = dict["content"] as? String else { return nil }
                var item = EvidenceItem(title: title, content: content)
                item.evidenceId = dict["evidence_id"] as? String
                return item
            }
        }

        if let phaseJSON = data["current_phase"],
           let phaseData = phaseJSON.data(using: .utf8),
           let phaseDict = try? JSONSerialization.jsonObject(with: phaseData) as? [String: Any] {
            store.game.currentPhase = parsePhaseInfo(phaseDict)
        }

        if status == "playing" || status == "voting" {
            if store.screen == .generating || store.screen == .lobby || store.screen == .home {
                if store.game.scenarioSetting.sceneImageUrl != nil {
                    store.screen = .intro
                } else {
                    store.screen = .playing
                }
            }
        } else if status == "ended" {
            store.screen = .ended
        }
    }

    private static func applyPhaseStarted(_ data: [String: String], store: AppStore) {
        let phase = parsePhaseInfo(stringDataToDict(data))
        store.game.currentPhase = phase
        store.game.localRemainingSec = phase?.remainingSec ?? phase?.durationSec ?? 0
        store.game.discoveries = []
        store.game.keptDiscoveryId = nil
        store.game.hasRevealedEvidence = false
        store.game.colocatedPlayers = []
        store.game.roomMessages = []
        if store.screen == .generating || store.screen == .lobby {
            store.screen = .playing
        }
        if !store.game.showPhaseTransition {
            store.game.showPhaseTransition = true
        }
        store.game.nextPhaseType = nil
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
            store.game.showPhaseTransition = false
        }
    }

    private static func applyPhaseTimer(_ data: [String: String], store: AppStore) {
        guard let remainingStr = data["remaining_sec"], let remaining = Int(remainingStr) else { return }
        store.game.localRemainingSec = remaining
        if let phase = store.game.currentPhase {
            store.game.currentPhase = PhaseInfo(
                phaseId: phase.phaseId,
                phaseType: phase.phaseType,
                phaseOrder: phase.phaseOrder,
                totalPhases: phase.totalPhases,
                durationSec: phase.durationSec,
                remainingSec: remaining,
                turnNumber: phase.turnNumber,
                totalTurns: phase.totalTurns,
                investigationLocations: phase.investigationLocations
            )
        }
    }

    private static func applyEnding(_ data: [String: String], store: AppStore) {
        let dict = stringDataToDict(data)
        guard let jsonData = try? JSONSerialization.data(withJSONObject: dict),
              let endingData = try? JSONDecoder().decode(EndingData.self, from: jsonData) else {
            store.setError("エンディングデータの解析に失敗しました", level: .transient)
            return
        }
        store.game.ending = endingData
        store.screen = .ended
    }

    private static func parsePhaseInfo(_ data: [String: Any]) -> PhaseInfo? {
        guard let phaseId = data["phase_id"] as? String,
              let phaseType = data["phase_type"] as? String,
              let phaseOrder = data["phase_order"] as? Int,
              let durationSec = data["duration_sec"] as? Int else { return nil }

        var locations: [InvestigationLocation]?
        if let locsData = data["investigation_locations"] as? [[String: Any]] {
            locations = locsData.compactMap { loc in
                guard let id = loc["id"] as? String,
                      let name = loc["name"] as? String else { return nil }
                return InvestigationLocation(id: id, name: name, description: loc["description"] as? String ?? "", features: loc["features"] as? [String])
            }
        }

        return PhaseInfo(
            phaseId: phaseId,
            phaseType: phaseType,
            phaseOrder: phaseOrder,
            totalPhases: data["total_phases"] as? Int ?? 3,
            durationSec: durationSec,
            remainingSec: data["remaining_sec"] as? Int ?? durationSec,
            turnNumber: data["turn_number"] as? Int ?? (phaseOrder / 3 + 1),
            totalTurns: data["total_turns"] as? Int ?? 3,
            investigationLocations: locations
        )
    }

    private static func stringDataToDict(_ data: [String: String]) -> [String: Any] {
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
