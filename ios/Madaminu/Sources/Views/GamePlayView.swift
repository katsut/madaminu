import DesignSystem
import SwiftUI
import WebKit

struct GamePlayView: View {
    @ObservedObject var store: AppStore
    @State private var showNotebook = false
    @State private var showDebug = false
    @State private var timer: Timer?
    @State private var endingRevealPhase: Int = 0  // 0=not started, 1=name, 2=verdict, 3=done

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            switch store.screen {
            case .intro:
                IntroView(store: store)
            case .playing:
                ZStack {
                    VStack(spacing: 0) {
                        errorBanner
                        phaseHeader
                        Divider().background(Color.mdSurface)

                        Group {
                            if let phase = store.game.currentPhase {
                                switch phase.phaseType {
                                case "opening":
                                    OpeningPhaseView(store: store)
                                case "planning":
                                    PlanningPhaseView(store: store)
                                case "investigation":
                                    InvestigationPhaseView(store: store)
                                case "discussion":
                                    DiscussionPhaseView(store: store)
                                case "voting":
                                    VotingPhaseView(store: store)
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

                    if store.game.showPhaseTransition {
                        PhaseTransitionOverlay(
                            phaseType: store.game.currentPhase?.phaseType ?? store.game.nextPhaseType ?? "",
                            turnNumber: store.game.currentPhase?.turnNumber ?? 1,
                            totalTurns: store.game.currentPhase?.totalTurns ?? 3,
                            durationSec: store.game.currentPhase?.durationSec ?? 0,
                            sceneImageUrl: store.game.scenarioSetting.sceneImageUrl,
                            travelNarrative: store.game.travelNarrative
                        )
                        .transition(.opacity)
                        .zIndex(100)
                    }
                }
                .animation(.easeInOut(duration: 0.5), value: store.game.showPhaseTransition)
            case .ended:
                if endingRevealPhase < 3, let ending = store.game.ending {
                    EndingRevealView(
                        ending: ending,
                        players: store.room.players,
                        phase: $endingRevealPhase
                    )
                } else {
                    endingView
                }
            default:
                EmptyView()
            }
        }
        .overlay {
            if showNotebook {
                ZStack(alignment: .bottom) {
                    NotebookView(store: store, isPresented: $showNotebook)

                    if ["opening", "planning", "discussion", "voting"].contains(store.game.currentPhase?.phaseType) {
                        HStack(spacing: Spacing.md) {
                            SpeechButton(store: store)
                        }
                        .padding(Spacing.md)
                        .background(Color.mdBackgroundSecondary)
                    }
                }
                .transition(.move(edge: .bottom))
            }
        }
        .animation(.easeInOut(duration: 0.25), value: showNotebook)
        .sheet(isPresented: $showDebug) {
            DebugInfoView(store: store)
        }
        .onAppear { startLocalTimer() }
        .onDisappear { stopLocalTimer() }
    }

    private func startLocalTimer() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak store] _ in
            DispatchQueue.main.async {
                guard let store else { return }
                if store.game.localRemainingSec > 0 && !store.game.isPaused {
                    store.game.localRemainingSec -= 1
                    if store.game.localRemainingSec <= 0 {
                        // Nudge server to advance if timer expired
                        store.sendWS(type: "phase.timer_expired")
                    }
                }
            }
        }
    }

    private func stopLocalTimer() {
        timer?.invalidate()
        timer = nil
    }

    private var errorBanner: some View {
        Group {
            if let error = store.errorMessage {
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
        .animation(.easeInOut(duration: 0.3), value: store.errorMessage)
    }

    private var phaseHeader: some View {
        HStack {
            if let phase = store.game.currentPhase {
                HStack(spacing: Spacing.xs) {
                    Circle()
                        .fill(phaseColor(phase.phaseType))
                        .frame(width: 10, height: 10)

                    VStack(alignment: .leading, spacing: 0) {
                        Text("ターン \(phase.turnNumber)/\(phase.totalTurns)")
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdTextMuted)
                        Text(phaseDisplayName(phase.phaseType))
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                }

                Spacer()

                Text(formatTime(store.game.localRemainingSec))
                    .font(.system(size: 18, weight: .bold, design: .monospaced))
                    .foregroundStyle(store.game.localRemainingSec <= 30 ? Color.mdAccent : Color.mdTextPrimary)
            } else {
                Text(store.screen == .ended ? "ゲーム終了" : "準備中...")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextSecondary)
                Spacer()
            }

            Circle()
                .fill(store.game.isConnected ? Color.mdSuccess : Color.mdAccent)
                .frame(width: 8, height: 8)

            Menu {
                Button("ホームに戻る", role: .destructive) { store.dispatch(.leaveRoom) }
                if store.room.isHost, store.screen != .ended {
                    if store.game.isPaused {
                        Button("再開") { store.dispatch(.resumePhase) }
                    } else {
                        Button("一時停止") { store.dispatch(.pausePhase) }
                    }
                    Button("フェーズを進める") { store.dispatch(.advancePhase) }
                    Button("時間を延長") { store.dispatch(.extendPhase) }
                    Button("デバッグ情報") { showDebug = true }
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .font(.mdTitle2)
                    .foregroundStyle(Color.mdTextSecondary)
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

            if ["opening", "planning", "discussion", "voting"].contains(store.game.currentPhase?.phaseType) {
                SpeechButton(store: store)
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

            Text(store.game.isConnected ? "ルーム準備中..." : "ルームに接続しています...")
                .font(.mdBody)
                .foregroundStyle(Color.mdTextSecondary)
        }
    }

    private var endingView: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                if let ending = store.game.ending {
                    // 1. Vote Results
                    if let counts = ending.voteCounts, !counts.isEmpty {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                Label("投票結果", systemImage: "hand.raised.fill")
                                    .font(.mdTitle2)
                                    .foregroundStyle(Color.mdAccent)

                                ForEach(counts.sorted(by: { $0.value > $1.value }), id: \.key) { name, count in
                                    HStack {
                                        Text(name)
                                            .font(.mdHeadline)
                                            .foregroundStyle(name == ending.arrestedName ? Color.mdAccent : Color.mdTextPrimary)
                                        Spacer()
                                        Text("\(count) 票")
                                            .font(.mdCallout)
                                            .foregroundStyle(Color.mdTextSecondary)
                                        if name == ending.arrestedName {
                                            Image(systemName: "lock.circle.fill")
                                                .foregroundStyle(Color.mdAccent)
                                            Text("監禁")
                                                .font(.mdCaption2)
                                                .foregroundStyle(Color.mdAccent)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // 2. Epilogue
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            Label("エピローグ", systemImage: "book.fill")
                                .font(.mdTitle2)
                                .foregroundStyle(Color.mdPrimary)

                            Text(ending.endingText)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextPrimary)
                        }
                    }

                    // 2.5. Criminal Epilogue
                    if let epilogue = ending.criminalEpilogue, !epilogue.isEmpty {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.md) {
                                Label("真相 — 犯人の告白", systemImage: "eye.trianglebadge.exclamationmark")
                                    .font(.mdTitle2)
                                    .foregroundStyle(Color.mdAccent)

                                Text(epilogue)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextPrimary)
                                    .italic()
                            }
                        }
                    }

                    // 3. Rankings
                    if let rankings = ending.rankings, !rankings.isEmpty {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                Label("最終スコア", systemImage: "trophy.fill")
                                    .font(.mdTitle2)
                                    .foregroundStyle(Color.mdWarning)

                                ForEach(Array(rankings.enumerated()), id: \.element.id) { index, rank in
                                    HStack(spacing: Spacing.sm) {
                                        Text(rankEmoji(index))
                                            .font(.system(size: 24))
                                            .frame(width: 32)
                                        PlayerAvatarView(playerId: rank.playerId, players: store.room.players, size: 36)
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(rank.characterName)
                                                .font(.mdHeadline)
                                                .foregroundStyle(Color.mdTextPrimary)
                                            Text("発言 \(rank.speechCount)回 / 証拠 \(rank.evidenceCount)件")
                                                .font(.mdCaption2)
                                                .foregroundStyle(Color.mdTextMuted)
                                        }
                                        Spacer()
                                        Text("\(rank.score) pt")
                                            .font(.system(size: 20, weight: .bold, design: .monospaced))
                                            .foregroundStyle(index == 0 ? Color.mdWarning : Color.mdTextPrimary)
                                    }
                                    if index < rankings.count - 1 {
                                        Divider()
                                    }
                                }
                            }
                        }
                    }

                    // 4. Objective Results
                    if let results = ending.objectiveResults, !results.isEmpty {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                Label("個人目的の達成状況", systemImage: "target")
                                    .font(.mdTitle2)
                                    .foregroundStyle(Color.mdInfo)

                                ForEach(Array(results.keys.sorted()), id: \.self) { playerId in
                                    if let result = results[playerId] {
                                        HStack(alignment: .top, spacing: Spacing.sm) {
                                            PlayerAvatarView(playerId: playerId, players: store.room.players, size: 28)
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

                    // 5. Character Reveals
                    if let reveals = ending.characterReveals, !reveals.isEmpty {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.md) {
                                Label("ネタバラシ", systemImage: "theatermasks.fill")
                                    .font(.mdTitle2)
                                    .foregroundStyle(Color.mdPrimary)

                                ForEach(reveals) { reveal in
                                    VStack(alignment: .leading, spacing: Spacing.xs) {
                                        HStack(spacing: Spacing.sm) {
                                            PlayerAvatarView(playerId: reveal.playerId, players: store.room.players, size: 32)
                                            Text(reveal.characterName)
                                                .font(.mdHeadline)
                                                .foregroundStyle(Color.mdTextPrimary)
                                            if let role = reveal.role {
                                                Text(roleLabel(role))
                                                    .font(.mdCaption2)
                                                    .padding(.horizontal, Spacing.xs)
                                                    .padding(.vertical, 2)
                                                    .background(roleColor(role).opacity(0.15))
                                                    .foregroundStyle(roleColor(role))
                                                    .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                            }
                                        }
                                        if let secret = reveal.secretInfo {
                                            Text(secret)
                                                .font(.mdCaption)
                                                .foregroundStyle(Color.mdTextSecondary)
                                        }
                                    }
                                    .padding(.vertical, Spacing.xs)
                                }
                            }
                        }
                    }

                    // Bottom buttons
                    HStack(spacing: Spacing.md) {
                        MDButton("もう一度見る", style: .secondary) {
                            endingRevealPhase = 0
                        }
                        MDButton("ホームに戻る") {
                            store.game.reset()
                            store.screen = .home
                        }
                    }
                } else {
                    ProgressView("エンディングを生成中...")
                        .tint(Color.mdPrimary)
                        .padding(Spacing.xl)
                }
            }
            .padding(Spacing.lg)
        }
    }

    private func rankEmoji(_ index: Int) -> String {
        switch index {
        case 0: "🥇"
        case 1: "🥈"
        case 2: "🥉"
        default: "\(index + 1)."
        }
    }

    private func roleLabel(_ role: String) -> String {
        switch role {
        case "criminal": "犯人"
        case "witness": "目撃者"
        case "related": "関係者"
        case "innocent": "一般人"
        default: role
        }
    }

    private func roleColor(_ role: String) -> Color {
        switch role {
        case "criminal": .mdAccent
        case "witness": .mdWarning
        case "related": .mdInfo
        case "innocent": .mdSuccess
        default: .mdTextMuted
        }
    }

    private func phaseColor(_ type: String) -> Color {
        switch type {
        case "opening": .mdSuccess
        case "discussion": .mdPrimary
        case "planning": .mdWarning
        case "investigation": .mdInfo
        case "voting": .mdAccent
        default: .mdTextMuted
        }
    }

    private func phaseDisplayName(_ type: String) -> String {
        switch type {
        case "opening": "自己紹介"
        case "discussion": "議論"
        case "planning": "調査計画"
        case "investigation": "調査"
        case "voting": "最終議論 & 投票"
        default: type
        }
    }

    private func formatTime(_ seconds: Int) -> String {
        let min = seconds / 60
        let sec = seconds % 60
        return String(format: "%d:%02d", min, sec)
    }

    private func playerName(_ playerId: String) -> String {
        store.room.players.first(where: { $0.id == playerId })?.characterName
            ?? store.room.players.first(where: { $0.id == playerId })?.displayName
            ?? playerId
    }
}

struct SpeechButton: View {
    @ObservedObject var store: AppStore

    var body: some View {
        if store.game.isSpeaking {
            MDButton("発言終了", style: .danger) {
                store.dispatch(.releaseSpeech)
            }
        } else {
            MDButton("発言する") {
                store.dispatch(.requestSpeech)
            }
            .disabled(store.game.currentSpeakerId != nil)
        }
    }
}

struct OpeningPhaseView: View {
    @ObservedObject var store: AppStore

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                GMGuideCard(
                    title: "自己紹介タイム",
                    message: "発言ボタンを押して、自分のキャラクターを紹介してください。\nこの集まりでの立場や、他のキャラクターとの関係を共有しましょう。"
                )

                if let speaker = store.game.currentSpeakerId {
                    let name = store.room.players.first(where: { $0.id == speaker })?.characterName ?? "誰か"
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

                if store.game.isSpeaking {
                    TranscriptView(store: store)
                }

                SpeechHistoryView(store: store)
            }
            .padding(Spacing.lg)
        }
    }
}

struct PlanningPhaseView: View {
    @ObservedObject var store: AppStore
    @State private var selectedLocationId: String?
    @State private var mapSvg: String?

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                GMGuideCard(
                    title: "調査計画",
                    message: "みんなで相談して、次に調べる場所を決めましょう。発言ボタンで話し合えます。制限時間になると、選んだ場所で調査が始まります。"
                )

                if let speaker = store.game.currentSpeakerId {
                    speakerBanner(speaker)
                }

                if store.game.isSpeaking {
                    TranscriptView(store: store)
                }

                if let svg = mapSvg {
                    ScrollView(.horizontal, showsIndicators: false) {
                        SVGWebView(svgContent: svg)
                            .frame(width: 500, height: 220)
                    }
                    .frame(height: 220)
                    .background(Color(red: 0.067, green: 0.067, blue: 0.094))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.mdSurface, lineWidth: 1)
                    )
                }

                if let locations = store.game.currentPhase?.investigationLocations {
                    Text("調査先を選択")
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdTextSecondary)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    ForEach(locations) { location in
                        let isSelected = selectedLocationId == location.id
                        Button {
                            withAnimation(.easeInOut(duration: 0.15)) {
                                if isSelected {
                                    selectedLocationId = nil
                                    store.dispatch(.selectInvestigation(locationId: nil))
                                } else {
                                    selectedLocationId = location.id
                                    store.dispatch(.selectInvestigation(locationId: location.id))
                                }
                            }
                            Task { await loadMap() }
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: Spacing.xxs) {
                                    Text(location.name)
                                        .font(.mdHeadline)
                                        .foregroundStyle(Color.mdTextPrimary)
                                    Text(location.description)
                                        .font(.mdCaption)
                                        .foregroundStyle(isSelected ? Color.mdTextPrimary : Color.mdTextSecondary)
                                    if let features = location.features, !features.isEmpty {
                                        Text(features.joined(separator: "・"))
                                            .font(.mdCaption)
                                            .foregroundStyle(Color.mdTextMuted)
                                    }
                                }
                                Spacer()
                                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                                    .font(.mdTitle2)
                                    .foregroundStyle(isSelected ? Color.mdSuccess : Color.mdTextMuted)
                            }
                            .padding(Spacing.md)
                            .background(isSelected ? Color.mdPrimary.opacity(0.15) : Color.mdSurface)
                            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))
                            .overlay(
                                RoundedRectangle(cornerRadius: CornerRadius.md)
                                    .stroke(isSelected ? Color.mdPrimary : Color.mdSurface, lineWidth: isSelected ? 2 : 0)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }

                SpeechHistoryView(store: store)
            }
            .padding(Spacing.lg)
        }
        .task { await loadMap() }
    }

    @MainActor private func loadMap() async {
        guard let mapPath = store.game.scenarioSetting.mapUrl else { return }
        var urlString = APIClient.defaultBaseURL + mapPath
        if let locId = selectedLocationId {
            urlString += "?highlight=\(locId)"
        }
        guard let url = URL(string: urlString) else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            mapSvg = String(data: data, encoding: .utf8)
        } catch {
            // ignore
        }
    }

    private func speakerBanner(_ speakerId: String) -> some View {
        let name = store.room.players.first(where: { $0.id == speakerId })?.characterName ?? "誰か"
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

struct InvestigationPhaseView: View {
    @ObservedObject var store: AppStore

    private var selectedLocation: InvestigationLocation? {
        guard let locationId = store.game.selectedLocationId,
              let locations = store.game.currentPhase?.investigationLocations else { return nil }
        return locations.first(where: { $0.id == locationId })
    }

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                if let location = selectedLocation {
                    GMGuideCard(
                        title: location.name,
                        message: "部屋の中を調べています。発見物から1つだけ持ち帰れます。\(store.game.discoveries.first?.canTamper == true ? "誰もいないので、1つすり替えることもできます。" : "")"
                    )
                } else {
                    GMGuideCard(
                        title: "調査フェーズ",
                        message: "調査結果を待っています..."
                    )
                }

                if !store.game.colocatedPlayers.isEmpty {
                    ColocatedPlayersView(store: store)
                }

                if store.game.discoveries.isEmpty {
                    ProgressView()
                        .tint(Color.mdPrimary)
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding(Spacing.xl)
                }

                if !store.game.discoveries.isEmpty {
                    Text("発見物")
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdTextSecondary)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    ForEach(store.game.discoveries) { discovery in
                        let isKept = store.game.keptDiscoveryId == discovery.id
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                HStack {
                                    Image(systemName: discovery.isTampered ? "arrow.triangle.2.circlepath" : "doc.text.magnifyingglass")
                                        .foregroundStyle(discovery.isTampered ? Color.mdWarning : Color.mdSuccess)
                                    Text(discovery.title)
                                        .font(.mdHeadline)
                                        .foregroundStyle(Color.mdTextPrimary)
                                    Spacer()
                                    if isKept {
                                        Text("持ち帰り")
                                            .font(.mdCaption2)
                                            .foregroundStyle(Color.mdSuccess)
                                            .padding(.horizontal, Spacing.xs)
                                            .padding(.vertical, Spacing.xxs)
                                            .background(Color.mdSuccess.opacity(0.15))
                                            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                    }
                                }
                                Text(discovery.content)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextPrimary)

                                if store.game.keptDiscoveryId == nil && !discovery.isTampered {
                                    HStack(spacing: Spacing.sm) {
                                        MDButton("持ち帰る", style: .primary) {
                                            store.dispatch(.keepEvidence(discoveryId: discovery.id))
                                        }
                                        if discovery.canTamper {
                                            MDButton("すり替える", style: .danger) {
                                                store.dispatch(.tamperEvidence(discoveryId: discovery.id))
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                if !store.game.colocatedPlayers.isEmpty {
                    RoomChatView(store: store)
                }
            }
            .padding(Spacing.lg)
        }
    }
}

struct ColocatedPlayersView: View {
    @ObservedObject var store: AppStore

    var body: some View {
        MDCard {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                Text("同行者")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)

                HStack(spacing: Spacing.md) {
                    ForEach(store.game.colocatedPlayers) { player in
                        VStack(spacing: Spacing.xxs) {
                            if let urlPath = player.portraitUrl,
                               let url = URL(string: APIClient.defaultBaseURL + urlPath + "?size=64") {
                                AsyncImage(url: url) { image in
                                    image.resizable().aspectRatio(contentMode: .fill)
                                } placeholder: {
                                    Circle().fill(Color.mdSurface)
                                }
                                .frame(width: 40, height: 40)
                                .clipShape(Circle())
                            } else {
                                Circle()
                                    .fill(Color.mdSurface)
                                    .frame(width: 40, height: 40)
                            }
                            Text(player.characterName)
                                .font(.mdCaption2)
                                .foregroundStyle(Color.mdTextSecondary)
                                .lineLimit(1)
                        }
                    }
                }
            }
        }
    }
}

struct RoomChatView: View {
    @ObservedObject var store: AppStore
    @State private var messageText = ""

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .foregroundStyle(Color.mdInfo)
                Text("同室のヒソヒソ話")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextPrimary)
            }

            ForEach(store.game.roomMessages) { msg in
                HStack(alignment: .top, spacing: Spacing.xs) {
                    Text(msg.senderName)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdPrimary)
                        .frame(width: 60, alignment: .leading)
                    Text(msg.text)
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)
                }
            }

            HStack(spacing: Spacing.xs) {
                TextField("メッセージ...", text: $messageText)
                    .font(.mdBody)
                    .textFieldStyle(.roundedBorder)

                Button {
                    guard !messageText.isEmpty else { return }
                    store.dispatch(.sendRoomMessage(text: messageText))
                    let myName = store.room.players.first(where: { $0.id == store.room.playerId })?.characterName ?? "自分"
                    store.game.roomMessages.append(RoomMessage(senderId: store.room.playerId ?? "", senderName: myName, text: messageText))
                    messageText = ""
                } label: {
                    Image(systemName: "paperplane.fill")
                        .foregroundStyle(Color.mdPrimary)
                }
            }
        }
        .padding(Spacing.md)
        .background(Color.mdSurface)
        .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))
    }
}

struct DiscussionPhaseView: View {
    @ObservedObject var store: AppStore
    @State private var showRevealSheet = false

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                GMGuideCard(
                    title: "議論フェーズ",
                    message: "任意のタイミングで証拠を提出することができます。発言をする際には必ず発言ボタンをONにし、マイクを有効にしてください。\n\n📋 口頭の主張: 1点  |  証拠カードの提出: 3点"
                )

                if let speaker = store.game.currentSpeakerId {
                    let name = store.room.players.first(where: { $0.id == speaker })?.characterName ?? "誰か"
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

                if store.game.isSpeaking {
                    TranscriptView(store: store)
                }

                if !store.notebook.evidences.isEmpty && !store.game.hasRevealedEvidence {
                    MDButton("証拠を公開する", style: .secondary) {
                        showRevealSheet = true
                    }
                }

                ForEach(store.game.revealedEvidences) { revealed in
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HStack(spacing: Spacing.sm) {
                                PlayerAvatarView(playerId: revealed.playerId, players: store.room.players, size: 32)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("\(revealed.playerName) が証拠を公開")
                                        .font(.mdCaption)
                                        .foregroundStyle(Color.mdWarning)
                                }
                                Spacer()
                                Image(systemName: "eye.fill")
                                    .foregroundStyle(Color.mdWarning)
                            }
                            Text(revealed.title)
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdTextPrimary)
                            Text(revealed.content)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextSecondary)
                        }
                    }
                }

                SpeechHistoryView(store: store)
            }
            .padding(Spacing.lg)
        }
        .sheet(isPresented: $showRevealSheet) {
            EvidenceRevealSheet(store: store, isPresented: $showRevealSheet)
        }
    }
}

struct SpeechHistoryView: View {
    @ObservedObject var store: AppStore

    var body: some View {
        if !store.game.speechHistory.isEmpty {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                Text("発言履歴")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)

                ForEach(store.game.speechHistory) { entry in
                    HStack(alignment: .top, spacing: Spacing.sm) {
                        PlayerAvatarView(playerId: entry.playerId, players: store.room.players, size: 28)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(entry.characterName)
                                .font(.mdCaption)
                                .foregroundStyle(Color.mdPrimary)
                            Text(entry.transcript)
                                .font(.mdCaption)
                                .foregroundStyle(Color.mdTextSecondary)
                        }
                    }
                }
            }
            .padding(Spacing.md)
            .background(Color.mdSurface)
            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))
        }
    }
}

struct EvidenceRevealSheet: View {
    @ObservedObject var store: AppStore
    @Binding var isPresented: Bool

    private var revealableEvidences: [EvidenceItem] {
        let revealedIds = Set(store.game.revealedEvidences.map { $0.title })
        return store.notebook.evidences.filter { evidence in
            !revealedIds.contains(evidence.title)
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.mdBackground.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: Spacing.md) {
                        Text("公開する証拠を選択")
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextSecondary)

                        if revealableEvidences.isEmpty {
                            Text("公開できる証拠がありません")
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextMuted)
                                .padding(Spacing.xl)
                        }

                        ForEach(revealableEvidences) { evidence in
                            MDCard {
                                VStack(alignment: .leading, spacing: Spacing.sm) {
                                    Text(evidence.title)
                                        .font(.mdHeadline)
                                        .foregroundStyle(Color.mdTextPrimary)
                                    Text(evidence.content)
                                        .font(.mdCaption)
                                        .foregroundStyle(Color.mdTextSecondary)
                                    MDButton("これを公開") {
                                        store.dispatch(.revealEvidence(evidenceId: evidence.evidenceId ?? evidence.id.uuidString))
                                        store.game.hasRevealedEvidence = true
                                        isPresented = false
                                    }
                                }
                            }
                        }
                    }
                    .padding(Spacing.lg)
                }
            }
            .navigationTitle("証拠の公開")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("やめる") { isPresented = false }
                }
            }
        }
    }
}

struct VotingPhaseView: View {
    @ObservedObject var store: AppStore
    @State private var selectedSuspect: String?

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                GMGuideCard(
                    title: "最終議論 & 投票",
                    message: "調査と議論の結果をもとに、犯人だと思う人物を選んで投票してください。話し合いながら投票できます。\n\n制限時間経過 or 全員の投票完了で結果発表に進みます。"
                )

                if store.game.totalHumanPlayers > 0 {
                    Text("投票状況: \(store.game.votedCount) / \(store.game.totalHumanPlayers) 人")
                        .font(.mdCallout)
                        .foregroundStyle(store.game.votedCount >= store.game.totalHumanPlayers ? Color.mdSuccess : Color.mdTextMuted)
                }

                ForEach(store.room.players) { player in
                    MDCard {
                        HStack(spacing: Spacing.sm) {
                            PlayerAvatarView(playerId: player.id, players: store.room.players, size: 36)
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
                        store.dispatch(.vote(suspectId: suspect))
                    }
                }

                if let speaker = store.game.currentSpeakerId {
                    let name = store.room.players.first(where: { $0.id == speaker })?.characterName ?? "誰か"
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

                if store.game.isSpeaking {
                    TranscriptView(store: store)
                }

                SpeechHistoryView(store: store)
            }
            .padding(Spacing.lg)
        }
    }
}

struct TranscriptView: View {
    @ObservedObject var store: AppStore

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

                Text(store.game.currentTranscript.isEmpty ? "話してください..." : store.game.currentTranscript)
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}

struct DebugInfoView: View {
    @ObservedObject var store: AppStore
    @State private var players: [DebugPlayerInfo] = []
    @State private var isLoading = true
    @State private var errorText: String?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                Color.mdBackground.ignoresSafeArea()

                if isLoading {
                    ProgressView()
                        .tint(Color.mdPrimary)
                } else if let error = errorText {
                    Text(error)
                        .font(.mdBody)
                        .foregroundStyle(Color.mdError)
                } else {
                    ScrollView {
                        VStack(spacing: Spacing.md) {
                            ForEach(players) { player in
                                MDCard {
                                    VStack(alignment: .leading, spacing: Spacing.sm) {
                                        HStack {
                                            Text(player.characterName ?? player.displayName)
                                                .font(.mdHeadline)
                                                .foregroundStyle(Color.mdTextPrimary)
                                            if player.isAI {
                                                Text("AI")
                                                    .font(.mdCaption)
                                                    .foregroundStyle(Color.mdInfo)
                                            }
                                            Spacer()
                                            if let role = player.role {
                                                Text(role)
                                                    .font(.mdCaption)
                                                    .foregroundStyle(Color.mdAccent)
                                            }
                                        }

                                        if let secret = player.secretInfo {
                                            VStack(alignment: .leading, spacing: Spacing.xxs) {
                                                Text("秘密情報")
                                                    .font(.mdCaption)
                                                    .foregroundStyle(Color.mdTextMuted)
                                                Text(secret)
                                                    .font(.mdBody)
                                                    .foregroundStyle(Color.mdTextSecondary)
                                            }
                                        }

                                        if let objective = player.objective {
                                            VStack(alignment: .leading, spacing: Spacing.xxs) {
                                                Text("目的")
                                                    .font(.mdCaption)
                                                    .foregroundStyle(Color.mdTextMuted)
                                                Text(objective)
                                                    .font(.mdBody)
                                                    .foregroundStyle(Color.mdTextSecondary)
                                            }
                                        }

                                        if !player.evidences.isEmpty {
                                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                                Text("手帳 (\(player.evidences.count))")
                                                    .font(.mdCaption)
                                                    .foregroundStyle(Color.mdTextMuted)
                                                ForEach(Array(player.evidences.enumerated()), id: \.offset) { _, ev in
                                                    VStack(alignment: .leading, spacing: Spacing.xxs) {
                                                        Text(ev.title)
                                                            .font(.mdCaption)
                                                            .foregroundStyle(Color.mdPrimary)
                                                        Text(ev.content)
                                                            .font(.mdCaption)
                                                            .foregroundStyle(Color.mdTextSecondary)
                                                    }
                                                    .padding(.vertical, Spacing.xxs)
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
            }
            .navigationTitle("デバッグ情報")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("閉じる") { dismiss() }
                }
            }
        }
        .task {
            await loadDebugInfo()
        }
    }

    @MainActor private func loadDebugInfo() async {
        guard let token = store.room.sessionToken else {
            errorText = "セッションがありません"
            isLoading = false
            return
        }

        do {
            let api = APIClient()
            let response = try await api.getDebugInfo(roomCode: store.room.roomCode, sessionToken: token)
            players = response.players
        } catch {
            errorText = "デバッグ情報の取得に失敗しました"
        }
        isLoading = false
    }
}

struct MapSheetView: View {
    @ObservedObject var store: AppStore
    @State private var svgData: String?
    @State private var isLoading = true
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                Color.mdBackground.ignoresSafeArea()

                if isLoading {
                    ProgressView()
                        .tint(Color.mdPrimary)
                } else if let svg = svgData {
                    SVGWebView(svgContent: svg)
                        .ignoresSafeArea(edges: .bottom)
                } else {
                    Text("マップを読み込めませんでした")
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
            .navigationTitle("マップ")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("閉じる") { dismiss() }
                }
            }
        }
        .task {
            await loadMap()
        }
    }

    @MainActor private func loadMap() async {
        guard let mapPath = store.game.scenarioSetting.mapUrl else {
            isLoading = false
            return
        }

        let urlString = APIClient.defaultBaseURL + mapPath
        guard let url = URL(string: urlString) else {
            isLoading = false
            return
        }

        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            svgData = String(data: data, encoding: .utf8)
        } catch {
            svgData = nil
        }
        isLoading = false
    }
}

struct SVGWebView: UIViewRepresentable {
    let svgContent: String

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        loadSVG(webView, svg: svgContent)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        if context.coordinator.lastSVG != svgContent {
            context.coordinator.lastSVG = svgContent
            loadSVG(webView, svg: svgContent)
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    class Coordinator {
        var lastSVG: String = ""
    }

    private func loadSVG(_ webView: WKWebView, svg: String) {
        let html = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=3.0, user-scalable=yes">
        <style>
            body { margin: 0; background: #111118; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
            svg { max-width: 100%; height: auto; }
        </style>
        </head>
        <body>
        \(svg)
        </body>
        </html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }
}

struct PhaseTransitionOverlay: View {
    let phaseType: String
    let turnNumber: Int
    let totalTurns: Int
    let durationSec: Int
    let sceneImageUrl: String?
    var travelNarrative: String? = nil

    var body: some View {
        ZStack {
            Color.black.opacity(0.85).ignoresSafeArea()

            if let urlString = sceneImageUrl,
               let url = URL(string: APIClient.defaultBaseURL + urlString + "?size=512") {
                AsyncImage(url: url) { image in
                    image.resizable().aspectRatio(contentMode: .fill)
                } placeholder: {
                    Color.clear
                }
                .ignoresSafeArea()
                .opacity(0.3)
            }

            VStack(spacing: Spacing.md) {
                Text("ターン \(turnNumber) / \(totalTurns)")
                    .font(.system(size: 14, weight: .bold, design: .monospaced))
                    .foregroundStyle(Color.mdTextMuted)
                    .tracking(4)

                Text(phaseTitle(phaseType))
                    .font(.system(size: 36, weight: .bold))
                    .foregroundStyle(Color.mdTextPrimary)

                Text(phaseSubtitle(phaseType))
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, Spacing.xl)

                VStack(alignment: .leading, spacing: Spacing.sm) {
                    ForEach(phaseGuide(phaseType), id: \.self) { step in
                        HStack(alignment: .top, spacing: Spacing.xs) {
                            Text("•")
                                .foregroundStyle(Color.mdPrimary)
                            Text(step)
                                .font(.mdCaption)
                                .foregroundStyle(Color.mdTextSecondary)
                        }
                    }
                }
                .padding(.horizontal, Spacing.xl)
                .padding(.top, Spacing.sm)

                if let narrative = travelNarrative, !narrative.isEmpty {
                    Text(narrative)
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)
                        .italic()
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, Spacing.xl)
                        .padding(.top, Spacing.sm)
                }

                if durationSec > 0 {
                    Text(formatDuration(durationSec))
                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                        .foregroundStyle(Color.mdTextMuted)
                        .padding(.top, Spacing.xs)
                } else {
                    ProgressView()
                        .tint(Color.mdTextMuted)
                        .padding(.top, Spacing.xs)
                }
            }
        }
    }

    private func phaseTitle(_ type: String) -> String {
        switch type {
        case "opening": "自己紹介"
        case "discussion": "議論"
        case "planning": "調査計画"
        case "investigation": "調査"
        case "voting": "最終議論 & 投票"
        case "ending": "結果発表"
        default: type
        }
    }

    private func phaseSubtitle(_ type: String) -> String {
        switch type {
        case "opening": "まずはお互いを知りましょう。自己紹介と状況の共有をしてください"
        case "discussion": "集めた情報をもとに推理を話し合いましょう"
        case "planning": "みんなで相談して、次に調べる場所を決めましょう"
        case "investigation": "選んだ場所で手がかりを探しましょう"
        case "voting": "最後の議論と投票です。犯人だと思う人物を選んでください"
        case "ending": "投票結果とエピローグを生成中です..."
        default: ""
        }
    }

    private func phaseGuide(_ type: String) -> [String] {
        switch type {
        case "opening":
            return [
                "発言ボタンを押して自己紹介をする",
                "他のキャラクターの話を聞いて関係性を把握する",
                "手帳で自分の情報を確認する",
            ]
        case "ending":
            return [
                "AIがエピローグを生成中です",
                "少々お待ちください...",
            ]
        case "discussion":
            return [
                "任意のタイミングで証拠を提出できる",
                "発言する際は必ず発言ボタンをONにし、マイクを有効にする",
                "口頭の主張: 1点 / 証拠カードの提出: 3点",
            ]
        case "planning":
            return [
                "マップを見て調べたい場所を1つ選ぶ",
                "発言ボタンで他のプレイヤーと相談できる",
                "制限時間後、選んだ場所で調査が始まる",
            ]
        case "investigation":
            return [
                "場所にあるものから1つ選んで調べる",
                "手がかりが見つかると手帳に記録される",
                "同じ場所の人とだけヒソヒソ話ができる",
            ]
        case "voting":
            return [
                "最後の議論をしてから投票する",
                "犯人だと思う人物を1人選ぶ",
                "全員の投票が揃うと結果発表",
            ]
        default:
            return []
        }
    }

    private func formatDuration(_ seconds: Int) -> String {
        let min = seconds / 60
        let sec = seconds % 60
        return sec > 0 ? "制限時間 \(min)分\(sec)秒" : "制限時間 \(min)分"
    }
}

struct GMGuideCard: View {
    let title: String
    let message: String

    var body: some View {
        MDCard {
            HStack(alignment: .top, spacing: Spacing.sm) {
                Image(systemName: "theatermasks.fill")
                    .font(.mdTitle2)
                    .foregroundStyle(Color.mdPrimary)

                VStack(alignment: .leading, spacing: Spacing.xxs) {
                    Text(title)
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdPrimary)
                    Text(message)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
        }
    }
}

struct EndingRevealView: View {
    let ending: EndingData
    let players: [PlayerInfo]
    @Binding var phase: Int
    @State private var textOpacity: Double = 0
    @State private var revealTask: Task<Void, Never>?

    private var arrestedPlayer: PlayerInfo? {
        guard let name = ending.arrestedName else { return nil }
        return players.first(where: { $0.characterName == name })
    }

    private var isTrueCriminal: Bool {
        guard let player = arrestedPlayer else { return false }
        return player.id == ending.trueCriminalId
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: Spacing.xl) {
                if phase == 0 || phase == 1 {
                    // Scene 1: "〇〇は・・・・"
                    VStack(spacing: Spacing.lg) {
                        if let player = arrestedPlayer {
                            PlayerAvatarView(playerId: player.id, players: players, size: 100)
                        }
                        Text("\(ending.arrestedName ?? "???") は・・・・")
                            .font(.system(size: 28, weight: .bold))
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                    .opacity(textOpacity)
                } else if phase == 2 {
                    // Scene 2: verdict
                    VStack(spacing: Spacing.lg) {
                        if let player = arrestedPlayer {
                            PlayerAvatarView(playerId: player.id, players: players, size: 100)
                        }
                        Text(isTrueCriminal ? "犯人でした" : "冤罪でした")
                            .font(.system(size: 40, weight: .black))
                            .foregroundStyle(isTrueCriminal ? Color.mdAccent : Color.mdInfo)
                        Text(isTrueCriminal ? "真犯人を見事に見抜きました" : "無実の人が監禁されてしまいました...")
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextSecondary)
                    }
                    .opacity(textOpacity)
                }
            }
        }
        .onAppear {
            startReveal()
        }
        .onDisappear {
            revealTask?.cancel()
        }
    }

    private func startReveal() {
        revealTask?.cancel()
        revealTask = Task { @MainActor in
            phase = 1
            withAnimation(.easeIn(duration: 1.5)) {
                textOpacity = 1
            }
            try? await Task.sleep(for: .seconds(4))
            guard !Task.isCancelled else { return }
            withAnimation(.easeOut(duration: 0.5)) {
                textOpacity = 0
            }
            try? await Task.sleep(for: .seconds(1))
            guard !Task.isCancelled else { return }
            phase = 2
            withAnimation(.easeIn(duration: 1.0)) {
                textOpacity = 1
            }
            try? await Task.sleep(for: .seconds(5))
            guard !Task.isCancelled else { return }
            phase = 3
        }
    }
}

struct PlayerAvatarView: View {
    let playerId: String?
    let players: [PlayerInfo]
    var size: CGFloat = 32

    private var portraitUrl: URL? {
        guard let pid = playerId,
              let player = players.first(where: { $0.id == pid }),
              let urlPath = player.portraitUrl else { return nil }
        return URL(string: APIClient.defaultBaseURL + urlPath + "?size=\(Int(size * 2))")
    }

    private var initial: String {
        guard let pid = playerId,
              let player = players.first(where: { $0.id == pid }),
              let name = player.characterName else { return "?" }
        return String(name.prefix(1))
    }

    var body: some View {
        if let url = portraitUrl {
            AsyncImage(url: url) { image in
                image.resizable().aspectRatio(contentMode: .fill)
            } placeholder: {
                Circle().fill(Color.mdSurface)
                    .overlay(Text(initial).font(.system(size: size * 0.4)).foregroundStyle(Color.mdTextMuted))
            }
            .frame(width: size, height: size)
            .clipShape(Circle())
        } else {
            Circle()
                .fill(Color.mdSurface)
                .frame(width: size, height: size)
                .overlay(Text(initial).font(.system(size: size * 0.4)).foregroundStyle(Color.mdTextMuted))
        }
    }
}
