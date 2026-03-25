import DesignSystem
import SwiftUI

struct IntroView: View {
    @Bindable var viewModel: GameViewModel
    @State private var currentPage = 0

    private let pageCount = 3

    var body: some View {
        VStack(spacing: 0) {
            pageIndicator

            TabView(selection: $currentPage) {
                storyIntroPage.tag(0)
                characterCardsPage.tag(1)
                mySecretPage.tag(2)
            }
            .tabViewStyle(.page(indexDisplayMode: .never))
            .animation(.easeInOut, value: currentPage)
        }
        .background(Color.mdBackground.ignoresSafeArea())
    }

    private var pageIndicator: some View {
        HStack(spacing: Spacing.xs) {
            ForEach(0..<pageCount, id: \.self) { i in
                Capsule()
                    .fill(i == currentPage ? Color.mdPrimary : Color.mdTextMuted.opacity(0.3))
                    .frame(width: i == currentPage ? 24 : 8, height: 8)
                    .animation(.easeInOut(duration: 0.2), value: currentPage)
            }
        }
        .padding(.top, Spacing.lg)
        .padding(.bottom, Spacing.sm)
    }

    private var storyIntroPage: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text("物語の始まり")
                .font(.mdLargeTitle)
                .foregroundStyle(Color.mdPrimary)

            if let setting = viewModel.scenarioSetting.location {
                Text("舞台: \(setting)")
                    .font(.mdTitle2)
                    .foregroundStyle(Color.mdTextPrimary)
            }

            if let situation = viewModel.scenarioSetting.situation {
                MDCard {
                    Text(situation)
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)
                }
            }

            if let victim = viewModel.scenarioSetting.victimName {
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
            }

            Spacer()

            Text("スワイプして続きを読む →")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)
                .padding(.bottom, Spacing.xl)
        }
        .padding(.horizontal, Spacing.lg)
    }

    private var characterCardsPage: some View {
        VStack(spacing: 0) {
            Text("登場人物")
                .font(.mdTitle)
                .foregroundStyle(Color.mdPrimary)
                .padding(.top, Spacing.md)

            ScrollView(.vertical) {
                VStack(spacing: Spacing.sm) {
                    ForEach(viewModel.players) { player in
                        MDCard {
                            HStack {
                                VStack(alignment: .leading, spacing: Spacing.xxs) {
                                    Text(player.characterName ?? player.displayName)
                                        .font(.mdHeadline)
                                        .foregroundStyle(Color.mdTextPrimary)
                                    Text(player.displayName)
                                        .font(.mdCaption)
                                        .foregroundStyle(Color.mdTextMuted)
                                }
                                Spacer()
                                if player.id == viewModel.playerId {
                                    Text("あなた")
                                        .font(.mdCaption2)
                                        .foregroundStyle(Color.mdPrimary)
                                        .padding(.horizontal, Spacing.xs)
                                        .padding(.vertical, Spacing.xxs)
                                        .background(Color.mdPrimary.opacity(0.15))
                                        .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.vertical, Spacing.sm)
            }

            Text("スワイプして続きを読む →")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)
                .padding(.bottom, Spacing.xl)
        }
    }

    private var mySecretPage: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text("あなたの秘密")
                .font(.mdTitle)
                .foregroundStyle(Color.mdAccent)

            if let role = viewModel.myRole {
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
            }

            if let secret = viewModel.mySecretInfo {
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
            }

            if let objective = viewModel.myObjective {
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
            }

            Spacer()

            MDButton("ゲームを始める") {
                withAnimation { viewModel.dismissIntro() }
            }
            .padding(.bottom, Spacing.xl)
        }
        .padding(.horizontal, Spacing.lg)
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
