import DesignSystem
import SwiftUI

struct IntroView: View {
    @ObservedObject var store: AppStore
    @State private var currentPage = 0
    @State private var selectedPlayer: PlayerInfo?

    private let pageCount = 3

    var body: some View {
        VStack(spacing: 0) {
            pageIndicator

            Group {
                switch currentPage {
                case 0: storyIntroPage
                case 1: characterCardsPage
                case 2: mySecretPage
                default: EmptyView()
                }
            }
            .frame(maxHeight: .infinity)

            navigationBar
        }
        .background(Color.mdBackground.ignoresSafeArea())
        .sheet(item: $selectedPlayer) { player in
            PlayerDetailSheet(player: player, isMe: player.id == store.room.playerId)
        }
    }

    private var pageIndicator: some View {
        HStack(spacing: Spacing.xs) {
            ForEach(0..<pageCount, id: \.self) { i in
                Capsule()
                    .fill(i == currentPage ? Color.mdPrimary : Color.mdTextMuted.opacity(0.3))
                    .frame(width: i == currentPage ? 24 : 8, height: 8)
            }
        }
        .padding(.top, Spacing.lg)
        .padding(.bottom, Spacing.sm)
        .animation(.easeInOut(duration: 0.2), value: currentPage)
    }

    private var navigationBar: some View {
        HStack(spacing: Spacing.md) {
            if currentPage > 0 {
                MDButton("← 戻る", style: .secondary) { currentPage -= 1 }
            }
            Spacer()
            if currentPage < pageCount - 1 {
                MDButton("次へ →") { currentPage += 1 }
            }
        }
        .padding(.horizontal, Spacing.lg)
        .padding(.bottom, Spacing.lg)
    }

    // MARK: - Page 1: Story

    private var storyIntroPage: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                Text("物語の始まり")
                    .font(.mdLargeTitle)
                    .foregroundStyle(Color.mdPrimary)
                    .padding(.top, Spacing.xl)

                if let urlString = store.game.scenarioSetting.sceneImageUrl,
                   let url = URL(string: APIClient.defaultBaseURL + urlString) {
                    AsyncImage(url: url) { image in
                        image.resizable().aspectRatio(contentMode: .fill)
                    } placeholder: {
                        ProgressView()
                    }
                    .frame(height: 200)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal, Spacing.lg)
                }

                if let setting = store.game.scenarioSetting.location {
                    Text("舞台: \(setting)")
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdTextPrimary)
                }

                if let situation = store.game.scenarioSetting.situation {
                    MDCard {
                        Text(situation)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                    .padding(.horizontal, Spacing.lg)
                }

                if let victim = store.game.scenarioSetting.victimName {
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            Label("被害者", systemImage: "person.slash")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdAccent)
                            Text(victim)
                                .font(.mdTitle2)
                                .foregroundStyle(Color.mdTextPrimary)
                            if let desc = store.game.scenarioSetting.victimDescription {
                                Text(desc)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextSecondary)
                            }
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                }

                Spacer().frame(height: Spacing.xl)
            }
        }
    }

    // MARK: - Page 2: Characters (simple cards, tap for detail)

    private var characterCardsPage: some View {
        VStack(spacing: 0) {
            Text("登場人物")
                .font(.mdTitle)
                .foregroundStyle(Color.mdPrimary)
                .padding(.top, Spacing.md)

            Text("タップして詳細を表示")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)

            ScrollView(.vertical) {
                VStack(spacing: Spacing.sm) {
                    ForEach(store.room.players) { player in
                        Button {
                            selectedPlayer = player
                        } label: {
                            MDCard {
                                HStack(spacing: Spacing.sm) {
                                    playerAvatar(player)

                                    VStack(alignment: .leading, spacing: Spacing.xxs) {
                                        Text(player.characterName ?? player.displayName)
                                            .font(.mdHeadline)
                                            .foregroundStyle(Color.mdTextPrimary)

                                        Text(player.displayName)
                                            .font(.mdCaption)
                                            .foregroundStyle(Color.mdTextMuted)
                                    }

                                    Spacer()

                                    if player.id == store.room.playerId {
                                        Text("あなた")
                                            .font(.mdCaption2)
                                            .foregroundStyle(Color.mdPrimary)
                                            .padding(.horizontal, Spacing.xs)
                                            .padding(.vertical, Spacing.xxs)
                                            .background(Color.mdPrimary.opacity(0.15))
                                            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                    }

                                    if player.isAI {
                                        Text("AI")
                                            .font(.mdCaption2)
                                            .foregroundStyle(Color.mdInfo)
                                            .padding(.horizontal, Spacing.xs)
                                            .padding(.vertical, Spacing.xxs)
                                            .background(Color.mdInfo.opacity(0.15))
                                            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                    }
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.vertical, Spacing.sm)
            }
        }
    }

    // MARK: - Page 3: My Secret

    private var mySecretPage: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                Text("あなたの秘密")
                    .font(.mdTitle)
                    .foregroundStyle(Color.mdAccent)
                    .padding(.top, Spacing.xl)

                if let role = store.game.myRole {
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Label("役割", systemImage: "theatermask.and.paintbrush")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdPrimary)
                            Text(roleDisplayName(role))
                                .font(.mdTitle2)
                                .foregroundStyle(Color.mdTextPrimary)
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                }

                if let secret = store.game.mySecretInfo {
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Label("秘密情報", systemImage: "lock.fill")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdAccent)
                            Text(secret)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextPrimary)
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                }

                if let objective = store.game.myObjective {
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Label("あなたの目的", systemImage: "target")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdWarning)
                            Text(objective)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextPrimary)
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                }

                Spacer().frame(height: Spacing.md)

                MDButton("ゲームを始める") {
                    withAnimation { store.dispatch(.dismissIntro) }
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.md)
            }
        }
    }

    // MARK: - Helpers

    @ViewBuilder
    private func playerAvatar(_ player: PlayerInfo) -> some View {
        if let urlString = player.portraitUrl,
           let url = URL(string: APIClient.defaultBaseURL + urlString) {
            AsyncImage(url: url) { image in
                image.resizable().aspectRatio(contentMode: .fill)
            } placeholder: {
                Image(systemName: "person.fill")
                    .font(.system(size: 20))
                    .foregroundStyle(Color.mdTextMuted)
                    .frame(width: 50, height: 50)
                    .background(Color.mdSurface)
            }
            .frame(width: 50, height: 50)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        } else {
            Image(systemName: "person.fill")
                .font(.system(size: 20))
                .foregroundStyle(Color.mdTextMuted)
                .frame(width: 50, height: 50)
                .background(Color.mdSurface)
                .clipShape(RoundedRectangle(cornerRadius: 8))
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

// MARK: - Player Detail Sheet

struct PlayerDetailSheet: View {
    let player: PlayerInfo
    let isMe: Bool
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Color.mdBackground.ignoresSafeArea()

            ScrollView {
                VStack(spacing: Spacing.lg) {
                    HStack {
                        Spacer()
                        Button { dismiss() } label: {
                            Image(systemName: "xmark")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdTextSecondary)
                        }
                    }

                    if let urlString = player.portraitUrl,
                       let url = URL(string: APIClient.defaultBaseURL + urlString) {
                        AsyncImage(url: url) { image in
                            image.resizable().aspectRatio(contentMode: .fill)
                        } placeholder: {
                            ProgressView()
                        }
                        .frame(width: 120, height: 120)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }

                    Text(player.characterName ?? player.displayName)
                        .font(.mdTitle)
                        .foregroundStyle(Color.mdTextPrimary)

                    HStack(spacing: Spacing.xs) {
                        Text("プレイヤー: \(player.displayName)")
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdTextMuted)

                        if isMe {
                            Text("あなた")
                                .font(.mdCaption2)
                                .foregroundStyle(Color.mdPrimary)
                                .padding(.horizontal, Spacing.xs)
                                .padding(.vertical, Spacing.xxs)
                                .background(Color.mdPrimary.opacity(0.15))
                                .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                        }

                        if player.isAI {
                            Text("AI")
                                .font(.mdCaption2)
                                .foregroundStyle(Color.mdInfo)
                                .padding(.horizontal, Spacing.xs)
                                .padding(.vertical, Spacing.xxs)
                                .background(Color.mdInfo.opacity(0.15))
                                .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                        }
                    }

                    if let personality = player.characterPersonality {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                Label("性格", systemImage: "brain.head.profile")
                                    .font(.mdHeadline)
                                    .foregroundStyle(Color.mdPrimary)
                                Text(personality)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextPrimary)
                            }
                        }
                    }

                    if let background = player.characterBackground {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                Label("経歴", systemImage: "book")
                                    .font(.mdHeadline)
                                    .foregroundStyle(Color.mdPrimary)
                                Text(background)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextPrimary)
                            }
                        }
                    }
                }
                .padding(Spacing.lg)
            }
        }
    }
}
