import DesignSystem
import SwiftUI

struct GamePlayView: View {
    @ObservedObject var controller: GameController
    @State private var showNotebook = false

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            switch controller.screen {
            case .intro:
                IntroView(controller: controller)
            case .playing:
                VStack(spacing: 0) {
                    errorBanner
                    phaseHeader
                    Divider().background(Color.mdSurface)

                    Group {
                        if let phase = controller.currentPhase {
                            switch phase.phaseType {
                            case "investigation":
                                InvestigationPhaseView(controller: controller)
                            case "discussion":
                                DiscussionPhaseView(controller: controller)
                            case "voting":
                                VotingPhaseView(controller: controller)
                            default:
                                waitingView
                            }
                        } else {
                            waitingView
                        }
                    }
                    .frame(maxHeight: .infinity)

                    bottomBar
                }
            case .ended:
                endingView
            default:
                EmptyView()
            }
        }
        .fullScreenCover(isPresented: $showNotebook) {
            NotebookView(controller: controller, isPresented: $showNotebook)
        }
    }

    private var errorBanner: some View {
        Group {
            if let error = controller.errorMessage {
                HStack(spacing: Spacing.xs) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(Color.mdBackground)
                    Text(error)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdBackground)
                    Spacer()
                }
                .padding(.horizontal, Spacing.md)
                .padding(.vertical, Spacing.sm)
                .background(Color.mdAccent)
                .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.3), value: controller.errorMessage)
    }

    private var phaseHeader: some View {
        HStack {
            if let phase = controller.currentPhase {
                HStack(spacing: Spacing.xs) {
                    Circle()
                        .fill(phaseColor(phase.phaseType))
                        .frame(width: 10, height: 10)

                    Text(phaseDisplayName(phase.phaseType))
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdTextPrimary)
                }

                Spacer()

                Text(formatTime(phase.remainingSec))
                    .font(.system(size: 18, weight: .bold, design: .monospaced))
                    .foregroundStyle(phase.remainingSec <= 30 ? Color.mdAccent : Color.mdTextPrimary)
            } else {
                Text(controller.screen == .ended ? "ゲーム終了" : "準備中...")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextSecondary)
                Spacer()
            }

            if controller.isHost, controller.screen != .ended {
                Menu {
                    Button("フェーズを進める") { controller.advancePhase() }
                    Button("時間を延長") { controller.extendPhase() }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
        }
        .padding(.horizontal, Spacing.lg)
        .padding(.vertical, Spacing.sm)
        .background(Color.mdBackgroundSecondary)
    }

    private var bottomBar: some View {
        HStack(spacing: Spacing.md) {
            MDButton("手帳", style: .secondary) {
                showNotebook = true
            }

            if controller.currentPhase?.phaseType == "discussion" || controller.currentPhase?.phaseType == "investigation" {
                SpeechButton(controller: controller)
            }
        }
        .padding(Spacing.md)
        .background(Color.mdBackgroundSecondary)
    }

    private var waitingView: some View {
        VStack(spacing: Spacing.md) {
            ProgressView()
                .tint(Color.mdPrimary)
                .scaleEffect(1.5)

            Text(controller.isConnected ? "ルーム準備中..." : "ルームに接続しています...")
                .font(.mdBody)
                .foregroundStyle(Color.mdTextSecondary)
        }
    }

    private var endingView: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                if let error = controller.errorMessage {
                    HStack(spacing: Spacing.xs) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(Color.mdBackground)
                        Text(error)
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdBackground)
                        Spacer()
                    }
                    .padding(.horizontal, Spacing.md)
                    .padding(.vertical, Spacing.sm)
                    .background(Color.mdAccent)
                    .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                }

                if let ending = controller.ending {
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            Text("真相")
                                .font(.mdTitle)
                                .foregroundStyle(Color.mdPrimary)

                            Text(ending.endingText)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextPrimary)
                        }
                    }

                    if let results = ending.objectiveResults {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                Text("個人目的の達成状況")
                                    .font(.mdHeadline)
                                    .foregroundStyle(Color.mdPrimary)

                                ForEach(Array(results.keys.sorted()), id: \.self) { playerId in
                                    if let result = results[playerId] {
                                        HStack(alignment: .top) {
                                            Image(systemName: result.achieved ? "checkmark.circle.fill" : "xmark.circle.fill")
                                                .foregroundStyle(result.achieved ? Color.mdSuccess : Color.mdAccent)
                                            VStack(alignment: .leading) {
                                                Text(playerName(playerId))
                                                    .font(.mdCallout)
                                                    .foregroundStyle(Color.mdTextPrimary)
                                                Text(result.description)
                                                    .font(.mdCaption)
                                                    .foregroundStyle(Color.mdTextSecondary)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }

    private func phaseColor(_ type: String) -> Color {
        switch type {
        case "investigation": .mdInfo
        case "discussion": .mdPrimary
        case "voting": .mdAccent
        default: .mdTextMuted
        }
    }

    private func phaseDisplayName(_ type: String) -> String {
        switch type {
        case "investigation": "調査フェーズ"
        case "discussion": "議論フェーズ"
        case "voting": "投票フェーズ"
        default: type
        }
    }

    private func formatTime(_ seconds: Int) -> String {
        let min = seconds / 60
        let sec = seconds % 60
        return String(format: "%d:%02d", min, sec)
    }

    private func playerName(_ playerId: String) -> String {
        controller.players.first(where: { $0.id == playerId })?.characterName
            ?? controller.players.first(where: { $0.id == playerId })?.displayName
            ?? playerId
    }
}

struct SpeechButton: View {
    @ObservedObject var controller: GameController

    var body: some View {
        if controller.isSpeaking {
            MDButton("発言終了", style: .danger) {
                controller.releaseSpeech()
            }
        } else {
            MDButton("発言する") {
                controller.requestSpeech()
            }
            .disabled(controller.currentSpeakerId != nil)
        }
    }
}

struct InvestigationPhaseView: View {
    @ObservedObject var controller: GameController

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                if let speaker = controller.currentSpeakerId {
                    speakerBanner(speaker)
                }

                if controller.isSpeaking {
                    TranscriptView(controller: controller)
                }

                if let locations = controller.currentPhase?.investigationLocations {
                    Text("調査可能な場所")
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdTextSecondary)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    ForEach(locations) { location in
                        MDCard {
                            HStack {
                                VStack(alignment: .leading, spacing: Spacing.xxs) {
                                    Text(location.name)
                                        .font(.mdHeadline)
                                        .foregroundStyle(Color.mdTextPrimary)
                                    Text(location.description)
                                        .font(.mdCaption)
                                        .foregroundStyle(Color.mdTextSecondary)
                                }
                                Spacer()
                                MDButton("調べる", style: .secondary) {
                                    controller.investigate(locationId: location.id)
                                }
                            }
                        }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }

    private func speakerBanner(_ speakerId: String) -> some View {
        let name = controller.players.first(where: { $0.id == speakerId })?.characterName ?? "誰か"
        return MDCard {
            HStack {
                Image(systemName: "mic.fill")
                    .foregroundStyle(Color.mdAccent)
                Text("\(name) が発言中")
                    .font(.mdCallout)
                    .foregroundStyle(Color.mdTextPrimary)
                Spacer()
            }
        }
    }
}

struct DiscussionPhaseView: View {
    @ObservedObject var controller: GameController

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                if let speaker = controller.currentSpeakerId {
                    let name = controller.players.first(where: { $0.id == speaker })?.characterName ?? "誰か"
                    MDCard {
                        HStack {
                            Image(systemName: "mic.fill")
                                .foregroundStyle(Color.mdAccent)
                            Text("\(name) が発言中")
                                .font(.mdCallout)
                                .foregroundStyle(Color.mdTextPrimary)
                            Spacer()
                        }
                    }
                }

                if controller.isSpeaking {
                    TranscriptView(controller: controller)
                }

                MDCard {
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Text("議論フェーズ")
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdPrimary)
                        Text("発言ボタンを押して、他のプレイヤーと議論しましょう。証拠や推理を共有してください。")
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextSecondary)
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }
}

struct VotingPhaseView: View {
    @ObservedObject var controller: GameController
    @State private var selectedSuspect: String?

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                Text("犯人だと思う人物に投票してください")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextSecondary)

                ForEach(controller.players) { player in
                    MDCard {
                        HStack {
                            VStack(alignment: .leading) {
                                Text(player.characterName ?? player.displayName)
                                    .font(.mdHeadline)
                                    .foregroundStyle(Color.mdTextPrimary)
                            }
                            Spacer()

                            if selectedSuspect == player.id {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(Color.mdAccent)
                            }
                        }
                    }
                    .onTapGesture {
                        selectedSuspect = player.id
                    }
                }

                if let suspect = selectedSuspect {
                    MDButton("投票する", style: .danger) {
                        controller.vote(suspectPlayerId: suspect)
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }
}

struct TranscriptView: View {
    @ObservedObject var controller: GameController

    var body: some View {
        MDCard {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                HStack {
                    Image(systemName: "mic.circle.fill")
                        .foregroundStyle(Color.mdAccent)
                    Text("録音中...")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdAccent)
                    Spacer()
                }

                Text(controller.currentTranscript.isEmpty ? "話してください..." : controller.currentTranscript)
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}
