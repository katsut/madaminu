import DesignSystem
import SwiftUI

private let randomNames = [
    "探偵・明智", "医師・白鳥", "記者・鷹野", "令嬢・桜庭", "教授・神谷",
    "バーテンダー・蓮", "画家・藤堂", "元軍人・黒崎", "占い師・月影", "シェフ・火野",
]

private let randomPersonalities = [
    "冷静沈着で観察力に優れる。少し皮肉屋だが正義感が強い。",
    "穏やかで知的。人当たりが良いが、どこか影がある。",
    "好奇心旺盛で行動的。真実を追い求める情熱家。",
    "上品で社交的。華やかな外見の裏に鋭い洞察力を持つ。",
    "博識で論理的。やや偏屈だが、根は優しい。",
    "寡黙だが聞き上手。人の秘密を知りすぎている。",
    "感受性が豊かで気まぐれ。芸術のためなら常識を超える。",
    "規律正しく実直。仲間を守ることに命をかける。",
    "神秘的で直感が鋭い。人の心を見透かすような瞳を持つ。",
    "情熱的で完璧主義。妥協を許さない職人肌。",
]

private let randomBackgrounds = [
    "元警察官。引退後は私立探偵として活動している。",
    "大学病院の外科医。最近、研究に没頭している。",
    "全国紙の社会部記者。スクープのためなら手段を選ばない。",
    "財閥の令嬢。慈善活動に熱心だが、家族との確執がある。",
    "大学の犯罪心理学教授。過去の未解決事件に執着している。",
    "老舗バーのマスター。この街の裏事情に詳しい。",
    "新進気鋭の画家。最近の個展が話題になったばかり。",
    "元自衛隊員。退役後はセキュリティ会社を経営している。",
    "人気占い師。予言が当たると評判だが、真偽は不明。",
    "ミシュラン星付きレストランのオーナーシェフ。",
]

struct CharacterCreationView: View {
    @Bindable var viewModel: RoomViewModel
    @State private var currentStep = 0
    @State private var characterName = ""
    @State private var personality = ""
    @State private var background = ""

    private let steps = ["名前", "性格", "背景", "確認"]

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.lg) {
                header
                stepIndicator
                ScrollView {
                    stepContent
                }
                .scrollDismissesKeyboard(.interactively)
                Spacer()
                navigationButtons
            }
            .padding(Spacing.lg)
        }
        .onTapGesture {
            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
        }
    }

    private var header: some View {
        HStack {
            Button {
                viewModel.showCharacterCreation = false
            } label: {
                Image(systemName: "xmark")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdTextSecondary)
            }

            Spacer()

            VStack(spacing: Spacing.xxs) {
                Text("キャラクター作成")
                    .font(.mdTitle2)
                    .foregroundStyle(Color.mdPrimary)

                Text("ステップ \(currentStep + 1) / \(steps.count)")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextSecondary)
            }

            Spacer()
            Spacer().frame(width: 24)
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
        case 3:
            confirmStep
        default:
            EmptyView()
        }
    }

    private var nameStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextField(label: "キャラクター名", text: $characterName, placeholder: "例: 探偵・明智")

            MDButton("🎲 AIにおまかせ", style: .ghost) {
                withAnimation { characterName = randomNames.randomElement()! }
            }

            MDCard {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Label("ヒント", systemImage: "lightbulb")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdPrimary)

                    Text("職業や特徴を含めると他のプレイヤーが覚えやすくなります。")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
        }
    }

    private var personalityStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextEditor(label: "性格・特徴", text: $personality)

            MDButton("🎲 AIにおまかせ", style: .ghost) {
                withAnimation { personality = randomPersonalities.randomElement()! }
            }

            MDCard {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Label("ヒント", systemImage: "lightbulb")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdPrimary)

                    Text("2〜3文で性格を描写してください。ロールプレイの指針になります。")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
        }
    }

    private var backgroundStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextEditor(label: "背景・経歴", text: $background)

            MDButton("🎲 AIにおまかせ", style: .ghost) {
                withAnimation { background = randomBackgrounds.randomElement()! }
            }

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
        }
    }

    private var confirmStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            Text("この内容で作成しますか？")
                .font(.mdHeadline)
                .foregroundStyle(Color.mdTextSecondary)

            MDCard {
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    HStack {
                        Text("名前")
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdTextMuted)
                        Spacer()
                    }
                    Text(characterName)
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdTextPrimary)

                    Divider()

                    HStack {
                        Text("性格")
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdTextMuted)
                        Spacer()
                    }
                    Text(personality)
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)

                    Divider()

                    HStack {
                        Text("背景")
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdTextMuted)
                        Spacer()
                    }
                    Text(background)
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)
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
            }
        }
    }

    private var isCurrentStepValid: Bool {
        switch currentStep {
        case 0: return !characterName.trimmingCharacters(in: .whitespaces).isEmpty
        case 1: return !personality.trimmingCharacters(in: .whitespaces).isEmpty
        case 2: return !background.trimmingCharacters(in: .whitespaces).isEmpty
        case 3: return true
        default: return false
        }
    }
}
