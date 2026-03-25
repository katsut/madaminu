import DesignSystem
import SwiftUI

struct IntroView: View {
    @Bindable var viewModel: GameViewModel
    @State private var currentPage = 0

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            TabView(selection: $currentPage) {
                storyIntroPage.tag(0)
                characterCardsPage.tag(1)
                mySecretPage.tag(2)
            }
            .tabViewStyle(.page(indexDisplayMode: .always))
        }
    }

    private var storyIntroPage: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                Spacer().frame(height: Spacing.xl)

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

                Text("スワイプして続きを読む →")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)

                Spacer()
            }
            .padding(Spacing.lg)
        }
    }

    private var characterCardsPage: some View {
        ScrollView {
            VStack(spacing: Spacing.md) {
                Spacer().frame(height: Spacing.lg)

                Text("登場人物")
                    .font(.mdTitle)
                    .foregroundStyle(Color.mdPrimary)

                ForEach(viewModel.players) { player in
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HStack {
                                Text(player.characterName ?? player.displayName)
                                    .font(.mdTitle2)
                                    .foregroundStyle(Color.mdTextPrimary)

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

                            Text(player.displayName)
                                .font(.mdCaption)
                                .foregroundStyle(Color.mdTextMuted)
                        }
                    }
                }

                Text("スワイプして続きを読む →")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)

                Spacer()
            }
            .padding(Spacing.lg)
        }
    }

    private var mySecretPage: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                Spacer().frame(height: Spacing.xl)

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

                MDButton("ゲームを始める") {
                    withAnimation { viewModel.dismissIntro() }
                }

                Spacer()
            }
            .padding(Spacing.lg)
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
