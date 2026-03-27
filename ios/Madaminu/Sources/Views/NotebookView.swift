import DesignSystem
import SwiftUI

struct NotebookView: View {
    @ObservedObject var store: AppStore
    @Binding var isPresented: Bool
    @State private var selectedTab = 0

    private let tabs = ["自分", "登場人物", "証拠", "メモ"]

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: 0) {
                header
                tabBar
                tabContent
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
        TabView(selection: $selectedTab) {
            myInfoPage.tag(0)
            playersPage.tag(1)
            evidencePage.tag(2)
            notesPage.tag(3)
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
                                   let url = URL(string: APIClient.defaultBaseURL + urlString) {
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

    // MARK: - Tab 4: Notes

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
