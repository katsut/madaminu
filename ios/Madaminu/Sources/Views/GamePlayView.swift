import DesignSystem
import SwiftUI

struct GamePlayView: View {
    @ObservedObject var viewModel: GameViewModel
    @State private var showNotebook = false

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            switch viewModel.screen {
            case .intro:
                IntroView(viewModel: viewModel)
            case .playing:
                VStack(spacing: 0) {
                    errorBanner
                    phaseHeader
                    Divider().background(Color.mdSurface)

                    Group {
                        if let phase = viewModel.currentPhase {
                            switch phase.phaseType {
                            case "investigation":
                                InvestigationPhaseView(viewModel: viewModel)
                            case "discussion":
                                DiscussionPhaseView(viewModel: viewModel)
                            case "voting":
                                VotingPhaseView(viewModel: viewModel)
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
            }
        }
        .fullScreenCover(isPresented: $showNotebook) {
            NotebookView(viewModel: viewModel, isPresented: $showNotebook)
        }
        .task {
            await viewModel.setup()
        }
        .onDisappear {
            viewModel.disconnect()
        }
    }

    private var errorBanner: some View {
        Group {
            if let error = viewModel.errorMessage {
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
        .animation(.easeInOut(duration: 0.3), value: viewModel.errorMessage)
    }

    private var phaseHeader: some View {
        HStack {
            if let phase = viewModel.currentPhase {
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
                Text(viewModel.gameStatus == "ended" ? "ゲーム終了" : "準備中...")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextSecondary)
                Spacer()
            }

            if viewModel.isHost, viewModel.gameStatus != "ended" {
                Menu {
                    Button("フェーズを進める") { viewModel.advancePhase() }
                    Button("時間を延長") { viewModel.extendPhase() }
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

            if viewModel.currentPhase?.phaseType == "discussion" || viewModel.currentPhase?.phaseType == "investigation" {
                SpeechButton(viewModel: viewModel)
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

            Text(viewModel.gameStatus.isEmpty ? "ルームに接続しています..." : "ルーム準備中...")
                .font(.mdBody)
                .foregroundStyle(Color.mdTextSecondary)
        }
    }

    private var endingView: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                if let error = viewModel.errorMessage {
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

                if let ending = viewModel.ending {
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
        viewModel.players.first(where: { $0.id == playerId })?.characterName
            ?? viewModel.players.first(where: { $0.id == playerId })?.displayName
            ?? playerId
    }
}

struct SpeechButton: View {
    @ObservedObject var viewModel: GameViewModel

    var body: some View {
        if viewModel.isSpeaking {
            MDButton("発言終了", style: .danger) {
                viewModel.releaseSpeech()
            }
        } else {
            MDButton("発言する") {
                viewModel.requestSpeech()
            }
            .disabled(viewModel.currentSpeakerId != nil)
        }
    }
}

struct InvestigationPhaseView: View {
    @ObservedObject var viewModel: GameViewModel

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                if let speaker = viewModel.currentSpeakerId {
                    speakerBanner(speaker)
                }

                if viewModel.isSpeaking {
                    TranscriptView(viewModel: viewModel)
                }

                if let locations = viewModel.currentPhase?.investigationLocations {
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
                                    viewModel.investigate(locationId: location.id)
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
        let name = viewModel.players.first(where: { $0.id == speakerId })?.characterName ?? "誰か"
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
    @ObservedObject var viewModel: GameViewModel

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                if let speaker = viewModel.currentSpeakerId {
                    let name = viewModel.players.first(where: { $0.id == speaker })?.characterName ?? "誰か"
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

                if viewModel.isSpeaking {
                    TranscriptView(viewModel: viewModel)
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
    @ObservedObject var viewModel: GameViewModel
    @State private var selectedSuspect: String?

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                Text("犯人だと思う人物に投票してください")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextSecondary)

                ForEach(viewModel.players) { player in
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
                        viewModel.vote(suspectPlayerId: suspect)
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }
}

struct TranscriptView: View {
    @ObservedObject var viewModel: GameViewModel

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

                Text(viewModel.currentTranscript.isEmpty ? "話してください..." : viewModel.currentTranscript)
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}
