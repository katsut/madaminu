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
    }
}
