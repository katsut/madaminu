import DesignSystem
import SwiftUI
import WebKit

struct GamePlayView: View {
    @ObservedObject var store: AppStore
    @State private var showNotebook = false
    @State private var showDebug = false
    @State private var timer: Timer?

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

                    if store.game.showPhaseTransition, let phase = store.game.currentPhase {
                        PhaseTransitionOverlay(
                            phase: phase,
                            sceneImageUrl: store.game.scenarioSetting.sceneImageUrl
                        )
                        .transition(.opacity)
                        .zIndex(100)
                    }
                }
                .animation(.easeInOut(duration: 0.5), value: store.game.showPhaseTransition)
            case .ended:
                endingView
            default:
                EmptyView()
            }
        }
        .fullScreenCover(isPresented: $showNotebook) {
            NotebookView(store: store, isPresented: $showNotebook)
        }
        .sheet(isPresented: $showDebug) {
            DebugInfoView(store: store)
        }
        .onAppear { startLocalTimer() }
        .onDisappear { stopLocalTimer() }
    }

    private func startLocalTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            DispatchQueue.main.async {
                if store.game.localRemainingSec > 0 {
                    store.game.localRemainingSec -= 1
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

            if store.room.isHost, store.screen != .ended {
                Menu {
                    Button("フェーズを進める") { store.dispatch(.advancePhase) }
                    Button("時間を延長") { store.dispatch(.extendPhase) }
                    Button("デバッグ情報") { showDebug = true }
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

            if ["planning", "discussion", "investigation"].contains(store.game.currentPhase?.phaseType) {
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
                    .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                }

                if let ending = store.game.ending {
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
        case "planning": .mdWarning
        case "investigation": .mdInfo
        case "discussion": .mdPrimary
        case "voting": .mdAccent
        default: .mdTextMuted
        }
    }

    private func phaseDisplayName(_ type: String) -> String {
        switch type {
        case "planning": "調査計画"
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
                            .id(selectedLocationId ?? "none")
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
    @State private var selectedLocationId: String?
    @State private var mapSvg: String?

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                GMGuideCard(
                    title: "調査フェーズ",
                    message: "調査したい場所を1つ選んでください。制限時間になると自動的に調査が実行されます。発言ボタンで他のプレイヤーと相談もできます。"
                )

                if let speaker = store.game.currentSpeakerId {
                    speakerBanner(speaker)
                }

                if store.game.isSpeaking {
                    TranscriptView(store: store)
                }

                // Embedded map
                if let svg = mapSvg {
                    ScrollView(.horizontal, showsIndicators: false) {
                        SVGWebView(svgContent: svg)
                            .frame(width: 500, height: 220)
                            .id(selectedLocationId ?? "none")
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

struct DiscussionPhaseView: View {
    @ObservedObject var store: AppStore

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                GMGuideCard(
                    title: "議論フェーズ",
                    message: "集めた証拠をもとに推理を述べましょう。発言ボタンを押して他のプレイヤーと議論してください。誰が怪しいか、何が起きたのかを話し合いましょう。"
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

            }
            .padding(Spacing.lg)
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
                    title: "投票フェーズ",
                    message: "調査と議論の結果をもとに、犯人だと思う人物を選んで投票してください。全員の投票が揃うと結果が発表されます。"
                )

                ForEach(store.room.players) { player in
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
                        store.dispatch(.vote(suspectId: suspect))
                    }
                }
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
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
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
        \(svgContent)
        </body>
        </html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }
}

struct PhaseTransitionOverlay: View {
    let phase: PhaseInfo
    let sceneImageUrl: String?

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

            VStack(spacing: Spacing.lg) {
                Text("PHASE \(phase.phaseOrder + 1) / \(phase.totalPhases)")
                    .font(.system(size: 16, weight: .bold, design: .monospaced))
                    .foregroundStyle(Color.mdTextMuted)
                    .tracking(4)

                Text(phaseTitle(phase.phaseType))
                    .font(.system(size: 36, weight: .bold))
                    .foregroundStyle(Color.mdTextPrimary)

                Text(phaseSubtitle(phase.phaseType))
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, Spacing.xl)
            }
        }
    }

    private func phaseTitle(_ type: String) -> String {
        switch type {
        case "planning": "調査計画"
        case "investigation": "調査フェーズ"
        case "discussion": "議論フェーズ"
        case "voting": "投票フェーズ"
        default: type
        }
    }

    private func phaseSubtitle(_ type: String) -> String {
        switch type {
        case "planning": "みんなで相談して、次に調べる場所を決めましょう"
        case "investigation": "選んだ場所で手がかりを探しましょう"
        case "discussion": "集めた情報をもとに推理を話し合いましょう"
        case "voting": "犯人だと思う人物に投票してください"
        default: ""
        }
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
