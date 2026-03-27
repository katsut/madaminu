enum AppAction {
    case createRoom(password: String?)
    case joinRoom(code: String, password: String?)
    case leaveRoom
    case showCharacterCreation
    case dismissCharacterCreation
    case createCharacter(name: String, gender: String, age: String, occupation: String, appearance: String, personality: String, background: String)
    case startGame
    case dismissIntro
    case requestSpeech
    case releaseSpeech
    case investigate(locationId: String)
    case vote(suspectId: String)
    case advancePhase
    case extendPhase
    case fetchRooms
    case fetchMyRooms
    case deleteRoom(roomCode: String)
    case rejoinRoom(sessionToken: String, playerId: String, roomCode: String)
    case refreshRoom
}
