import DesignSystem
import SwiftUI

struct IntroView: View {
    @ObservedObject var controller: GameStore
    @State private var currentPage = 0

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
            .animation(.easeInOut(duration: 0.3), value: currentPage)

            navigationBar
        }
        .background(Color.mdBackground.ignoresSafeArea())
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
                MDButton("← 戻る", style: .secondary) {
                    currentPage -= 1
                }
            }

            Spacer()

            if currentPage < pageCount - 1 {
                MDButton("次へ →") {
                    currentPage += 1
                }
            }
        }
        .padding(.horizontal, Spacing.lg)
        .padding(.bottom, Spacing.lg)
    }

    private var storyIntroPage: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text("物語の始まり")
                .font(.mdLargeTitle)
                .foregroundStyle(Color.mdPrimary)

            if let setting = controller.scenarioSetting.location {
                Text("舞台: \(setting)")
                    .font(.mdTitle2)
                    .foregroundStyle(Color.mdTextPrimary)
            }

            if let situation = controller.scenarioSetting.situation {
                MDCard {
                    Text(situation)
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)
                }
                .padding(.horizontal, Spacing.lg)
            }

            if let victim = controller.scenarioSetting.victimName {
                MDCard {
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Label("被害者", systemImage: "person.slash")
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdAccent)
                        Text(victim)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                }
                .padding(.horizontal, Spacing.lg)
            }

            Spacer()
        }
    }

    private var characterCardsPage: some View {
        VStack(spacing: 0) {
            Text("登場人物")
                .font(.mdTitle)
                .foregroundStyle(Color.mdPrimary)
                .padding(.top, Spacing.md)

            ScrollView(.vertical) {
                VStack(spacing: Spacing.sm) {
                    ForEach(controller.players) { player in
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                HStack {
                                    Text(player.characterName ?? player.displayName)
                                        .font(.mdTitle2)
                                        .foregroundStyle(Color.mdTextPrimary)
                                    Spacer()
                                    if player.id == controller.playerId {
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
                                    Text(personality)
                                        .font(.mdCaption)
                                        .foregroundStyle(Color.mdTextSecondary)
                                        .lineLimit(3)
                                }

                                if let background = player.characterBackground {
                                    Text(background)
                                        .font(.mdCaption)
                                        .foregroundStyle(Color.mdTextMuted)
                                        .lineLimit(3)
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.vertical, Spacing.sm)
            }
        }
    }

    private var mySecretPage: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text("あなたの秘密")
                .font(.mdTitle)
                .foregroundStyle(Color.mdAccent)

            if let role = controller.myRole {
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

            if let secret = controller.mySecretInfo {
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

            if let objective = controller.myObjective {
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

            Spacer()

            MDButton("ゲームを始める") {
                withAnimation { controller.dismissIntro() }
            }
            .padding(.horizontal, Spacing.lg)
            .padding(.bottom, Spacing.md)
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
