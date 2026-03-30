import DesignSystem
import SwiftUI

struct NotebookView: View {
    @ObservedObject var store: AppStore
    @Binding var isPresented: Bool
    @State private var selectedTab = 0

    private var tabs: [String] {
        var t = ["自分", "登場人物", "証拠", "議論", "メモ"]
        if store.game.scenarioSetting.mapUrl != nil {
            t.insert("マップ", at: 2)
        }
        return t
    }

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: 0) {
                header
                tabBar
                tabContent
            }
            .onChange(of: tabs.count) {
                if selectedTab >= tabs.count {
                    selectedTab = 0
                }
            }
        }
    }

    private var header: some View {
        HStack {
            Text("個人手帳")
                .font(.mdTitle)
                .foregroundStyle(Color.mdPrimary)
            Spacer()
            Button { isPresented = false } label: {
                Image(systemName: "xmark")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextSecondary)
            }
        }
        .padding(.horizontal, Spacing.lg)
        .padding(.top, Spacing.lg)
        .padding(.bottom, Spacing.sm)
    }

    private var tabBar: some View {
        HStack(spacing: 0) {
            ForEach(0..<tabs.count, id: \.self) { index in
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) { selectedTab = index }
                } label: {
                    VStack(spacing: Spacing.xxs) {
                        Text(tabs[index])
                            .font(.mdCallout)
                            .foregroundStyle(selectedTab == index ? Color.mdPrimary : Color.mdTextMuted)
                        Rectangle()
                            .fill(selectedTab == index ? Color.mdPrimary : Color.clear)
                            .frame(height: 2)
                    }
                }
                .frame(maxWidth: .infinity)
            }
        }
        .padding(.horizontal, Spacing.md)
    }

    private var tabContent: some View {
        let hasMap = store.game.scenarioSetting.mapUrl != nil
        return TabView(selection: $selectedTab) {
            myInfoPage.tag(0)
            playersPage.tag(1)
            if hasMap {
                mapPage.tag(2)
                evidencePage.tag(3)
                discussionLogPage.tag(4)
                notesPage.tag(5)
            } else {
                evidencePage.tag(2)
                discussionLogPage.tag(3)
                notesPage.tag(4)
            }
        }
        .tabViewStyle(.page(indexDisplayMode: .never))
        .animation(.easeInOut(duration: 0.2), value: selectedTab)
    }

    // MARK: - Tab 1: My Info

    private var myInfoPage: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                MDCard {
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        Label("キャラクター情報", systemImage: "person.fill")
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdPrimary)

                        if let role = store.game.myRole {
                            HStack {
                                Text("役割")
                                    .font(.mdCaption)
                                    .foregroundStyle(Color.mdTextMuted)
                                Spacer()
                                Text(roleDisplayName(role))
                                    .font(.mdCallout)
                                    .foregroundStyle(Color.mdTextPrimary)
                            }
                        }

                        if let secret = store.game.mySecretInfo {
                            VStack(alignment: .leading, spacing: Spacing.xxs) {
                                Text("秘密")
                                    .font(.mdCaption)
                                    .foregroundStyle(Color.mdAccent)
                                Text(secret)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextPrimary)
                            }
                        }
                    }
                }

                if let objective = store.game.myObjective {
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Label("個人目的", systemImage: "target")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdWarning)

                            Text(objective)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextPrimary)

                            Text("※ 他のプレイヤーにバレてはいけません")
                                .font(.mdCaption2)
                                .foregroundStyle(Color.mdAccent)
                        }
                    }
                }

                if let me = store.room.players.first(where: { $0.id == store.room.playerId }),
                   let publicInfo = me.publicInfo, !publicInfo.isEmpty {
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Label("この集まりでの立場", systemImage: "person.2")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdInfo)
                            Text(publicInfo)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextPrimary)
                        }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }

    // MARK: - Tab 2: Players

    private var playersPage: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                ForEach(store.room.players) { player in
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HStack(spacing: Spacing.sm) {
                                if let urlString = player.portraitUrl,
                                   let url = URL(string: APIClient.defaultBaseURL + urlString + "?size=100") {
                                    AsyncImage(url: url) { image in
                                        image.resizable().aspectRatio(contentMode: .fill)
                                    } placeholder: {
                                        Image(systemName: "person.fill")
                                            .foregroundStyle(Color.mdTextMuted)
                                            .frame(width: 50, height: 50)
                                            .background(Color.mdSurface)
                                    }
                                    .frame(width: 50, height: 50)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))
                                }

                                VStack(alignment: .leading, spacing: Spacing.xxs) {
                                    HStack(spacing: Spacing.xs) {
                                        Text(player.characterName ?? player.displayName)
                                            .font(.mdHeadline)
                                            .foregroundStyle(Color.mdTextPrimary)
                                        if player.id == store.room.playerId {
                                            Text("自分")
                                                .font(.mdCaption2)
                                                .foregroundStyle(Color.mdPrimary)
                                                .padding(.horizontal, Spacing.xs)
                                                .padding(.vertical, 1)
                                                .background(Color.mdPrimary.opacity(0.15))
                                                .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                        }
                                    }
                                    HStack(spacing: Spacing.xs) {
                                        if let gender = player.characterGender, !gender.isEmpty {
                                            Text(gender).font(.mdCaption2).foregroundStyle(Color.mdTextMuted)
                                        }
                                        if let age = player.characterAge, !age.isEmpty, age != "不明" {
                                            Text("\(age)歳").font(.mdCaption2).foregroundStyle(Color.mdTextMuted)
                                        }
                                        if let occupation = player.characterOccupation, !occupation.isEmpty {
                                            Text(occupation).font(.mdCaption2).foregroundStyle(Color.mdTextMuted)
                                        }
                                    }
                                }
                                Spacer()
                            }

                            if let publicInfo = player.publicInfo, !publicInfo.isEmpty {
                                Text(publicInfo)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextSecondary)
                            }

                            if let personality = player.characterPersonality {
                                Text(personality)
                                    .font(.mdCaption)
                                    .foregroundStyle(Color.mdTextMuted)
                            }
                        }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }

    // MARK: - Tab: Map

    private var mapPage: some View {
        MapSheetView(store: store)
    }

    // MARK: - Tab 3: Evidence

    private var evidencePage: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                HStack {
                    Label("証拠カード", systemImage: "doc.text.magnifyingglass")
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdInfo)
                    Spacer()
                    Text("\(store.notebook.evidences.count)件")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextMuted)
                }

                if store.notebook.evidences.isEmpty {
                    MDCard {
                        Text("まだ証拠はありません")
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextMuted)
                            .frame(maxWidth: .infinity, alignment: .center)
                    }
                } else {
                    ForEach(store.notebook.evidences) { evidence in
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.xxs) {
                                Text(evidence.title)
                                    .font(.mdHeadline)
                                    .foregroundStyle(Color.mdTextPrimary)
                                Text(evidence.content)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextSecondary)
                            }
                        }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }

    // MARK: - Tab: Discussion Log

    private var discussionLogPage: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                HStack {
                    Label("議論の記録", systemImage: "text.bubble")
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdInfo)
                    Spacer()
                    Text("\(store.notebook.discussionLogs.count)ターン")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextMuted)
                }

                if store.notebook.discussionLogs.isEmpty {
                    MDCard {
                        Text("まだ議論の記録はありません")
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextMuted)
                            .frame(maxWidth: .infinity, alignment: .center)
                    }
                } else {
                    ForEach(store.notebook.discussionLogs) { log in
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            Text("ターン \(log.turnNumber)")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdPrimary)

                            if !log.reveals.isEmpty {
                                ForEach(log.reveals) { revealed in
                                    HStack(alignment: .top, spacing: Spacing.sm) {
                                        PlayerAvatarView(playerId: revealed.playerId, players: store.room.players, size: 24)
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text("\(revealed.playerName)が証拠を提出")
                                                .font(.mdCaption)
                                                .foregroundStyle(Color.mdWarning)
                                            Text(revealed.title)
                                                .font(.mdCallout)
                                                .foregroundStyle(Color.mdTextPrimary)
                                        }
                                    }
                                }
                            }

                            if !log.speeches.isEmpty {
                                ForEach(log.speeches) { entry in
                                    HStack(alignment: .top, spacing: Spacing.sm) {
                                        PlayerAvatarView(playerId: entry.playerId, players: store.room.players, size: 24)
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
                        }
                        .padding(Spacing.md)
                        .background(Color.mdSurface)
                        .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }

    // MARK: - Tab: Notes

    private var notesPage: some View {
        VStack(spacing: Spacing.md) {
            Label("メモ", systemImage: "pencil.and.outline")
                .font(.mdHeadline)
                .foregroundStyle(Color.mdTextSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)

            MDTextEditor(label: "", text: Binding(
                get: { store.notebook.notes },
                set: { store.notebook.notes = $0 }
            ), minHeight: 200)

            Spacer()
        }
        .padding(Spacing.lg)
    }

    // MARK: - Helpers

    private func roleDisplayName(_ role: String) -> String {
        switch role {
        case "criminal": "犯人"
        case "witness": "目撃者"
        case "related": "関係者"
        case "innocent": "一般人"
        default: role
        }
    }
}
