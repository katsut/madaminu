import Combine
import Foundation

final class GamePlayStore: ObservableObject, @unchecked Sendable {
    @Published var scenarioSetting = ScenarioSettingData()
    @Published var mySecretInfo: String?
    @Published var myObjective: String?
    @Published var myRole: String?
    @Published var currentPhase: PhaseInfo?
    @Published var currentSpeakerId: String?
    @Published var ending: EndingData?
    @Published var isSpeaking = false
    @Published var currentTranscript = ""
    @Published var isConnected = false
    @Published var showPhaseTransition = false
    @Published var isPaused = false
    @Published var localRemainingSec: Int = 0
    @Published var selectedLocationId: String?
    @Published var selectedFeature: String?
    @Published var roomMessages: [RoomMessage] = []
    @Published var colocatedPlayers: [ColocatedPlayer] = []
    @Published var discoveries: [DiscoveryItem] = []
    @Published var keptDiscoveryId: String?
    @Published var revealedEvidences: [RevealedEvidence] = []
    @Published var hasRevealedEvidence = false
    @Published var speechHistory: [SpeechEntry] = []
    @Published var introReady = false
    @Published var introReadyCount = 0

    // Preparation checklist
    @Published var aiPlayersReady = false
    @Published var scenarioReady = false
    @Published var sceneImageReady = false
    @Published var portraitsReady = false
    @Published var allReady = false

    func reset() {
        scenarioSetting = ScenarioSettingData()
        mySecretInfo = nil
        myObjective = nil
        myRole = nil
        currentPhase = nil
        currentSpeakerId = nil
        ending = nil
        isSpeaking = false
        currentTranscript = ""
        isConnected = false
        showPhaseTransition = false
        isPaused = false
        localRemainingSec = 0
        selectedLocationId = nil
        selectedFeature = nil
        roomMessages = []
        colocatedPlayers = []
        discoveries = []
        keptDiscoveryId = nil
        revealedEvidences = []
        hasRevealedEvidence = false
        speechHistory = []
        introReady = false
        introReadyCount = 0
        aiPlayersReady = false
        scenarioReady = false
        sceneImageReady = false
        portraitsReady = false
        allReady = false
    }
}
