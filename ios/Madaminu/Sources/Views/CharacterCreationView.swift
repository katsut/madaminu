import DesignSystem
import SwiftUI

struct CharacterCreationView: View {
    @Bindable var viewModel: RoomViewModel
    @State private var currentStep = 0
    @State private var characterName = ""
    @State private var personality = ""
    @State private var background = ""

    private let steps = ["名前", "性格", "背景"]

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.lg) {
                header
                stepIndicator
                stepContent
                Spacer()
                navigationButtons
            }
            .padding(Spacing.lg)
        }
    }

    private var header: some View {
        VStack(spacing: Spacing.xs) {
            Text("キャラクター作成")
                .font(.mdTitle)
                .foregroundStyle(Color.mdPrimary)

            Text("あなたのキャラクターを作りましょう")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextSecondary)
        }
    }

    private var stepIndicator: some View {
        HStack(spacing: Spacing.sm) {
            ForEach(0..<steps.count, id: \.self) { index in
                HStack(spacing: Spacing.xxs) {
                    Circle()
                        .fill(index <= currentStep ? Color.mdPrimary : Color.mdTextMuted.opacity(0.3))
                        .frame(width: 8, height: 8)

                    if index < steps.count - 1 {
                        Rectangle()
                            .fill(index < currentStep ? Color.mdPrimary : Color.mdTextMuted.opacity(0.3))
                            .frame(height: 2)
                    }
                }
            }
        }
        .padding(.horizontal, Spacing.xl)
    }

    @ViewBuilder
    private var stepContent: some View {
        switch currentStep {
        case 0:
            nameStep
        case 1:
            personalityStep
        case 2:
            backgroundStep
        default:
            EmptyView()
        }
    }

    private var nameStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextField(label: "キャラクター名", text: $characterName, placeholder: "例: 探偵・明智")

            MDCard {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Label("ヒント", systemImage: "lightbulb")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdPrimary)

                    Text("日本語の名前やニックネームがおすすめです。職業や特徴を含めると他のプレイヤーが覚えやすくなります。")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
        }
    }

    private var personalityStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextEditor(label: "性格・特徴", text: $personality)

            MDCard {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Label("ヒント", systemImage: "lightbulb")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdPrimary)

                    Text("2〜3文で性格を描写してください。ゲーム中のロールプレイの指針になります。")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
        }
    }

    private var backgroundStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextEditor(label: "背景・経歴", text: $background)

            MDCard {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Label("ヒント", systemImage: "lightbulb")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdPrimary)

                    Text("キャラクターの経歴や立場を書いてください。AIがシナリオに組み込みます。")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }

            previewCard
        }
    }

    private var previewCard: some View {
        MDCard {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                Text("プレビュー")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdPrimary)

                VStack(alignment: .leading, spacing: Spacing.xxs) {
                    Text(characterName.isEmpty ? "（名前未入力）" : characterName)
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdTextPrimary)

                    Text(personality.isEmpty ? "（性格未入力）" : personality)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextSecondary)

                    Text(background.isEmpty ? "（背景未入力）" : background)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextMuted)
                }
            }
        }
    }

    private var navigationButtons: some View {
        HStack(spacing: Spacing.md) {
            if currentStep > 0 {
                MDButton("戻る", style: .secondary) {
                    withAnimation { currentStep -= 1 }
                }
            }

            if currentStep < steps.count - 1 {
                MDButton("次へ") {
                    withAnimation { currentStep += 1 }
                }
                .disabled(!isCurrentStepValid)
            } else {
                MDButton("作成", isLoading: viewModel.isLoading) {
                    Task {
                        await viewModel.createCharacter(
                            name: characterName,
                            personality: personality,
                            background: background
                        )
                    }
                }
                .disabled(!isAllValid)
            }
        }
    }

    private var isCurrentStepValid: Bool {
        switch currentStep {
        case 0: return !characterName.trimmingCharacters(in: .whitespaces).isEmpty
        case 1: return !personality.trimmingCharacters(in: .whitespaces).isEmpty
        case 2: return !background.trimmingCharacters(in: .whitespaces).isEmpty
        default: return false
        }
    }

    private var isAllValid: Bool {
        !characterName.trimmingCharacters(in: .whitespaces).isEmpty
            && !personality.trimmingCharacters(in: .whitespaces).isEmpty
            && !background.trimmingCharacters(in: .whitespaces).isEmpty
    }
}
