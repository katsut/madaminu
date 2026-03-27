enum AppAction {
    case createRoom(password: String?)
    case joinRoom(code: String, password: String?)
    case leaveRoom
    case showCharacterCreation
    case dismissCharacterCreation
    case createCharacter(name: String, nameKana: String, gender: String, age: String, occupation: String, appearance: String, personality: String, background: String)
    case toggleReady
    case startGame
    case dismissIntro
    case introReady
    case requestSpeech
    case releaseSpeech
    case investigate(locationId: String)
    case selectInvestigation(locationId: String?)
    case selectFeature(feature: String)
    case keepEvidence(discoveryId: String)
    case tamperEvidence(discoveryId: String)
    case revealEvidence(evidenceId: String)
    case sendRoomMessage(text: String)
    case vote(suspectId: String)
    case advancePhase
    case extendPhase
    case fetchRooms
    case fetchMyRooms
    case deleteRoom(roomCode: String)
    case rejoinRoom(sessionToken: String, playerId: String, roomCode: String, status: String)
    case refreshRoom
}
