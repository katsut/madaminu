import DesignSystem
import SwiftUI

struct NotebookView: View {
    @ObservedObject var store: AppStore
    @Binding var isPresented: Bool
    @State private var selectedPlayer: PlayerInfo?

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: Spacing.md) {
                    header
                    characterSection
                    objectiveSection
                    playersSection
                    evidenceSection
                    notesSection
                }
                .padding(Spacing.lg)
            }
        }
        .sheet(item: $selectedPlayer) { player in
            PlayerDetailSheet(player: player, isMe: player.id == store.room.playerId)
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
    }

    private var characterSection: some View {
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
    }

    private var objectiveSection: some View {
        Group {
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
        }
    }

    private var evidenceSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
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
                    .transition(.asymmetric(insertion: .slide, removal: .opacity))
                }
            }
        }
        .animation(.easeInOut, value: store.notebook.evidences.count)
    }

    private var playersSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Label("登場人物", systemImage: "person.3.fill")
                .font(.mdHeadline)
                .foregroundStyle(Color.mdTextSecondary)

            ForEach(store.room.players) { player in
                Button { selectedPlayer = player } label: {
                    MDCard {
                        HStack(spacing: Spacing.sm) {
                            if let urlString = player.portraitUrl,
                               let url = URL(string: APIClient.defaultBaseURL + urlString) {
                                AsyncImage(url: url) { image in
                                    image.resizable().aspectRatio(contentMode: .fill)
                                } placeholder: {
                                    Image(systemName: "person.fill")
                                        .foregroundStyle(Color.mdTextMuted)
                                        .frame(width: 40, height: 40)
                                        .background(Color.mdSurface)
                                }
                                .frame(width: 40, height: 40)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
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
                                if let occupation = player.characterOccupation, !occupation.isEmpty {
                                    Text(occupation)
                                        .font(.mdCaption)
                                        .foregroundStyle(Color.mdTextMuted)
                                }
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.mdCaption)
                                .foregroundStyle(Color.mdTextMuted)
                        }
                    }
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var notesSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Label("メモ", systemImage: "pencil.and.outline")
                .font(.mdHeadline)
                .foregroundStyle(Color.mdTextSecondary)

            MDTextEditor(label: "", text: Binding(
                get: { store.notebook.notes },
                set: { store.notebook.notes = $0 }
            ), minHeight: 120)
        }
    }

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
