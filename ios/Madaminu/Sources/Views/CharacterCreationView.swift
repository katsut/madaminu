import DesignSystem
import SwiftUI

private struct CharacterTemplate {
    let name: String
    let gender: String
    let age: String
    let occupation: String
    let appearance: String
    let personality: String
    let background: String
}

private let characterTemplates: [CharacterTemplate] = [
    CharacterTemplate(
        name: "探偵・明智 小五郎",
        gender: "男",
        age: "45",
        occupation: "私立探偵",
        appearance: "鋭い目つきで、常にトレンチコートを羽織っている。",
        personality: "鋭い観察眼と論理的思考の持ち主。飄々としているが、事件の核心に迫ると表情が一変する。他人の嘘を見抜くのが得意。",
        background: "警視庁捜査一課の元エース刑事。10年前に担当した事件で無実の人間を追い詰めた過去があり、辞職。以来、私立探偵として活動している。"
    ),
    CharacterTemplate(
        name: "外科医・白鳥 麗子",
        gender: "女",
        age: "38",
        occupation: "心臓外科医",
        appearance: "知性と美貌を兼ね備え、常に白衣を着こなしている。",
        personality: "完璧主義者。患者の前では温かく穏やかだが、プライベートでは冷徹な一面を見せる。常に理性的に物事を判断する。",
        background: "国内トップクラスの大学病院でチーフを務める。最近、論文のデータ改竄疑惑が持ち上がっている。"
    ),
    CharacterTemplate(
        name: "記者・鷹野 翔太",
        gender: "男",
        age: "32",
        occupation: "新聞記者",
        appearance: "常にメモ帳を持ち歩き、髪はいつも少し乱れている。",
        personality: "正義感が強く、不正を許さない熱血漢。口は悪いが裏表がなく、信頼を寄せる人は多い。",
        background: "全国紙の社会部エース記者。半年前、同僚が不審な事故で亡くなり、その裏に陰謀があると確信している。"
    ),
    CharacterTemplate(
        name: "令嬢・桜庭 華",
        gender: "女",
        age: "26",
        occupation: "財閥令嬢",
        appearance: "華やかなドレスに身を包み、品のある佇まい。",
        personality: "華やかな笑顔の裏に鋼の意志を秘めた令嬢。人の感情の機微に敏感で、相手の心理を読み取る能力に長けている。",
        background: "桜庭財閥の一人娘。父親が急逝した後、若くして実権を握ることになった。父の死が本当に病死だったのか疑問を持ち始めている。"
    ),
    CharacterTemplate(
        name: "教授・神谷 一郎",
        gender: "男",
        age: "62",
        occupation: "大学教授",
        appearance: "白髪交じりの髪に銀縁眼鏡。パイプを咥えている。",
        personality: "犯罪心理学の権威。温厚で紳士的だが、研究テーマに関しては頑固で、一度信じたことは容易に覆さない。",
        background: "東都大学の犯罪心理学教授。30年以上にわたり犯罪事例を分析してきた。退官間近で、最後の大仕事にしたいと考えている。"
    ),
    CharacterTemplate(
        name: "バーテンダー・蓮",
        gender: "男",
        age: "50",
        occupation: "バーテンダー",
        appearance: "物静かで表情を読ませない。整った身なりで清潔感がある。",
        personality: "必要最小限の言葉しか発しないが、その一言一言に重みがある。人の話を聞くのが上手い。",
        background: "銀座の老舗バーのマスター。実は元公安警察官で、潜入捜査中の事件をきっかけに警察を去った。"
    ),
    CharacterTemplate(
        name: "画家・藤堂 美月",
        gender: "女",
        age: "29",
        occupation: "画家",
        appearance: "繊細な雰囲気で、指先に絵の具の跡が残っている。",
        personality: "繊細な感性と爆発的な情熱を併せ持つ芸術家。人間の「闇」を描くことに執着している。",
        background: "若くして国際的な美術賞を受賞。代表作のモデルが一年前に失踪し、参考人として事情聴取を受けた過去がある。"
    ),
    CharacterTemplate(
        name: "実業家・黒崎 剛",
        gender: "男",
        age: "47",
        occupation: "セキュリティ会社社長",
        appearance: "がっしりした体格。鋭い目つきで威圧感がある。",
        personality: "カリスマ的なリーダーシップと冷徹な判断力。部下からの信頼は厚いが、敵には容赦がない。",
        background: "元自衛隊の特殊部隊員。除隊後にセキュリティ会社を起業し、10年で業界最大手に成長させた。"
    ),
    CharacterTemplate(
        name: "占い師・月影 沙耶",
        gender: "女",
        age: "35",
        occupation: "占い師",
        appearance: "ミステリアスな雰囲気。大きなイヤリングと深い紫色の衣装。",
        personality: "神秘的な佇まいの裏に鋭い知性と冷静な分析力が隠されている。人の弱みを見抜く才能がある。",
        background: "テレビで人気の占い師。元は大学で心理学を研究していたが、倫理問題で学術界を追われた。"
    ),
    CharacterTemplate(
        name: "シェフ・火野 龍之介",
        gender: "男",
        age: "40",
        occupation: "シェフ",
        appearance: "大柄で力強い体格。情熱的な目をしている。",
        personality: "料理に対する情熱は誰にも負けない完璧主義者。感情の起伏が激しいが、根は純粋で人情味がある。",
        background: "パリで修業後、帰国して開いたレストランがミシュラン二つ星を獲得。パリ時代の師匠のレシピを盗んだという告発がある。"
    ),
]

struct CharacterCreationView: View {
    @ObservedObject var store: AppStore
    @State private var currentStep = 0
    @State private var characterName = ""
    @State private var gender = "不明"
    @State private var age = ""
    @State private var occupation = ""
    @State private var appearance = ""
    @State private var personality = ""
    @State private var background = ""

    private let steps = ["名前", "基本情報", "外見・性格", "経歴", "確認"]
    private let genderOptions = ["男", "女", "不明"]

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
                store.dispatch(.dismissCharacterCreation)
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
            basicInfoStep
        case 2:
            appearancePersonalityStep
        case 3:
            backgroundStep
        case 4:
            confirmStep
        default:
            EmptyView()
        }
    }

    private var nameStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextField(label: "キャラクター名", text: $characterName, placeholder: "例: 探偵・明智 小五郎")

            HStack(spacing: Spacing.sm) {
                MDButton("🎲 名前だけ", style: .ghost) {
                    withAnimation { characterName = characterTemplates.randomElement()!.name }
                }
                MDButton("🎲 全部おまかせ", style: .ghost) {
                    let t = characterTemplates.randomElement()!
                    withAnimation {
                        characterName = t.name
                        gender = t.gender
                        age = t.age
                        occupation = t.occupation
                        appearance = t.appearance
                        personality = t.personality
                        background = t.background
                    }
                }
            }
        }
    }

    private var basicInfoStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            Text("性別")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextSecondary)

            HStack(spacing: Spacing.sm) {
                ForEach(genderOptions, id: \.self) { option in
                    MDButton(option, style: gender == option ? .primary : .ghost) {
                        withAnimation { gender = option }
                    }
                }
            }

            MDTextField(label: "年齢", text: $age, placeholder: "例: 45")
                .keyboardType(.numberPad)

            MDTextField(label: "職業", text: $occupation, placeholder: "例: 私立探偵")
        }
    }

    private var appearancePersonalityStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextEditor(label: "外見の特徴", text: $appearance)

            MDTextEditor(label: "性格", text: $personality)

            MDButton("🎲 AIにおまかせ", style: .ghost) {
                let t = characterTemplates.randomElement()!
                withAnimation {
                    appearance = t.appearance
                    personality = t.personality
                }
            }
        }
    }

    private var backgroundStep: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            MDTextEditor(label: "経歴", text: $background)

            MDButton("🎲 AIにおまかせ", style: .ghost) {
                withAnimation { background = characterTemplates.randomElement()!.background }
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
                    confirmRow("名前", value: characterName)
                    Divider()
                    confirmRow("性別", value: gender)
                    Divider()
                    confirmRow("年齢", value: age.isEmpty ? "不明" : age)
                    Divider()
                    confirmRow("職業", value: occupation.isEmpty ? "未設定" : occupation)
                    Divider()
                    confirmRow("外見", value: appearance.isEmpty ? "未設定" : appearance)
                    Divider()
                    confirmRow("性格", value: personality)
                    Divider()
                    confirmRow("経歴", value: background)
                }
            }
        }
    }

    private func confirmRow(_ label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            Text(label)
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)
            Text(value)
                .font(.mdBody)
                .foregroundStyle(Color.mdTextPrimary)
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
                MDButton("作成", isLoading: store.isLoading) {
                    store.dispatch(.createCharacter(
                        name: characterName,
                        gender: gender,
                        age: age.isEmpty ? "不明" : age,
                        occupation: occupation,
                        appearance: appearance,
                        personality: personality,
                        background: background
                    ))
                }
            }
        }
    }

    private var isCurrentStepValid: Bool {
        switch currentStep {
        case 0: return !characterName.trimmingCharacters(in: .whitespaces).isEmpty
        case 1: return true
        case 2: return !personality.trimmingCharacters(in: .whitespaces).isEmpty
        case 3: return !background.trimmingCharacters(in: .whitespaces).isEmpty
        case 4: return true
        default: return false
        }
    }
}
