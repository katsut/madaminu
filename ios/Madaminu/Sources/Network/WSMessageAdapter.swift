import Foundation

struct WSMessageAdapter {
    static func apply(type: String, data: [String: String], store: AppStore) {
        print("[WS] recv: \(type)")
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
        case "game.generation_failed":
            store.setError("シナリオ生成に失敗しました。もう一度お試しください。", level: .transient)
            store.game.reset()
            store.screen = .lobby

        // Speech
        case "speech.granted":
            store.game.isSpeaking = true
            store.startRecording()
        case "speech.active":
            store.game.currentSpeakerId = data["player_id"]
        case "speech":
            store.game.currentSpeakerId = nil
            let playerId = data["player_id"]
            let characterName = data["character_name"] ?? ""
            let transcript = data["transcript"] ?? ""
            if !transcript.isEmpty {
                store.game.speechHistory.append(SpeechEntry(playerId: playerId, characterName: characterName, transcript: transcript))
            }

        // Evidence
        case "evidence_revealed":
            let playerId = data["player_id"] ?? ""
            let playerName = data["player_name"] ?? "不明"
            let title = data["title"] ?? ""
            let content = data["content"] ?? ""
            store.game.revealedEvidences.insert(
                RevealedEvidence(playerId: playerId, playerName: playerName, title: title, content: content),
                at: 0
            )
            if playerId != store.room.playerId {
                store.notebook.evidences.append(EvidenceItem(title: "[\(playerName)] \(title)", content: content))
            }

        // Vote
        case "vote_cast":
            if let votedStr = data["voted_count"], let totalStr = data["total_human"],
               let voted = Int(votedStr), let total = Int(totalStr) {
                store.game.votedCount = voted
                store.game.totalHumanPlayers = total
            }

        // Room message
        case "room_message":
            let senderId = data["sender_id"] ?? ""
            let senderName = data["sender_name"] ?? ""
            let text = data["text"] ?? ""
            store.game.roomMessages.append(RoomMessage(senderId: senderId, senderName: senderName, text: text))

        // Intro
        case "intro.ready.count":
            if let countStr = data["count"], let count = Int(countStr) {
                store.game.introReadyCount = count
            }
        case "intro.all_ready":
            if store.screen == .intro {
                store.screen = .playing
            }
        case "intro.start_game":
            if store.screen == .intro {
                store.screen = .playing
            }

        // Connection
        case "player.connected", "player.disconnected":
            break

        // Error
        case "error":
            let code = data["code"] ?? ""
            let msg = data["message"] ?? code
            if !msg.isEmpty {
                print("[WS] recv error: \(code) \(msg)")
                store.setError(msg, level: .transient)
            }

        case "ping":
            store.sendWS(type: "pong")

        default:
            print("[WS] Unknown: \(type)")
        }
    }

    // MARK: - game.state

    private static func applyGameState(_ data: [String: String], store: AppStore) {
        let status = data["status"] ?? ""

        // Secret info
        if let secret = data["my_secret_info"] { store.game.mySecretInfo = secret }
        if let objective = data["my_objective"] { store.game.myObjective = objective }
        if let role = data["my_role"] { store.game.myRole = role }

        // Scenario
        if let settingJSON = data["scenario_setting"],
           let settingData = settingJSON.data(using: .utf8),
           let setting = try? JSONSerialization.jsonObject(with: settingData) as? [String: Any] {
            store.game.scenarioSetting.location = setting["location"] as? String
            store.game.scenarioSetting.situation = setting["situation"] as? String
        }
        if let sceneUrl = data["scene_image_url"] { store.game.scenarioSetting.sceneImageUrl = sceneUrl }
        if let victimUrl = data["victim_image_url"] { store.game.scenarioSetting.victimImageUrl = victimUrl }
        if let mapUrl = data["map_url"] { store.game.scenarioSetting.mapUrl = mapUrl }

        if let victimJSON = data["victim"],
           let victimData = victimJSON.data(using: .utf8),
           let victim = try? JSONSerialization.jsonObject(with: victimData) as? [String: Any] {
            store.game.scenarioSetting.victimName = victim["name"] as? String
            store.game.scenarioSetting.victimDescription = victim["description"] as? String
        }

        // Players
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

        // Evidences
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

        // Phase — detect transition via phase_id comparison
        let previousPhaseId = store.game.currentPhase?.phaseId
        var newPhase: PhaseInfo?

        if let phaseJSON = data["current_phase"],
           let phaseData = phaseJSON.data(using: .utf8),
           let phaseDict = try? JSONSerialization.jsonObject(with: phaseData) as? [String: Any] {
            newPhase = parsePhaseInfo(phaseDict)
        }

        // Parse discoveries_status from phase info
        var discStatus = "pending"
        if let phaseJSON = data["current_phase"],
           let phaseData = phaseJSON.data(using: .utf8),
           let phaseDict = try? JSONSerialization.jsonObject(with: phaseData) as? [String: Any] {
            discStatus = phaseDict["discoveries_status"] as? String ?? "pending"
        }

        let phaseChanged = newPhase?.phaseId != previousPhaseId
        let becameReady = discStatus == "ready" && store.game.discoveriesStatus != "ready"

        if phaseChanged && newPhase != nil {
            // Save discussion log before clearing
            let prevType = store.game.currentPhase?.phaseType ?? ""
            if prevType == "discussion" {
                store.notebook.addDiscussionLog(
                    turnNumber: store.game.currentPhase?.turnNumber ?? 1,
                    speeches: store.game.speechHistory,
                    reveals: store.game.revealedEvidences
                )
            }

            // 1st game.state: phase changed, show transition overlay
            store.game.showPhaseTransition = true

            // Clear phase-specific state (keep speech/evidence history across phases)
            store.game.discoveries = []
            store.game.keptDiscoveryId = nil
            store.game.hasRevealedEvidence = false
            store.game.colocatedPlayers = []
            store.game.roomMessages = []
            store.game.travelNarrative = nil
        }

        if becameReady {
            // 2nd game.state: phase ready, dismiss transition overlay, start timer
            store.game.showPhaseTransition = false
            if let phase = newPhase {
                store.game.localRemainingSec = phase.remainingSec
            }
        }

        // Discoveries from game.state
        if let discJSON = data["my_discoveries"],
           let discData = discJSON.data(using: .utf8),
           let discArray = try? JSONSerialization.jsonObject(with: discData) as? [[String: Any]] {
            store.game.discoveries = discArray.compactMap { d in
                guard let id = d["id"] as? String,
                      let title = d["title"] as? String,
                      let content = d["content"] as? String else { return nil }
                return DiscoveryItem(id: id, title: title, content: content, canTamper: false)
            }
        }

        // Update phase and status
        store.game.currentPhase = newPhase
        store.game.discoveriesStatus = discStatus

        // Ending
        if status == "ended" {
            if let endingJSON = data["ending"],
               let endingData = endingJSON.data(using: .utf8),
               let endingObj = try? JSONDecoder().decode(EndingData.self, from: endingData) {
                store.game.ending = endingObj
            }
            store.screen = .ended
            return
        }

        // Screen transition
        if status == "playing" || status == "voting" {
            if store.screen == .generating || store.screen == .lobby || store.screen == .home {
                // If game has a current phase, go straight to playing (rejoin case)
                if newPhase != nil {
                    store.screen = .playing
                } else if store.game.scenarioSetting.sceneImageUrl != nil {
                    store.screen = .intro
                } else {
                    store.screen = .playing
                }
            }
        }
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
}
