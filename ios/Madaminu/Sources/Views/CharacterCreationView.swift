import DesignSystem
import SwiftUI

private struct CharacterTemplate {
    let name: String
    let personality: String
    let background: String
}

private let characterTemplates: [CharacterTemplate] = [
    CharacterTemplate(
        name: "探偵・明智 小五郎",
        personality: "鋭い観察眼と論理的思考の持ち主。一見すると飄々としているが、事件の核心に迫ると表情が一変する。他人の嘘を見抜くのが得意で、何気ない会話から矛盾を突くのが常套手段。ただし共感力に乏しく、真実を追い求めるあまり人を傷つけることもある。紅茶を飲みながら考え事をする癖がある。",
        background: "警視庁捜査一課の元エース刑事。10年前に担当した連続殺人事件で無実の人間を追い詰めてしまった過去があり、責任を取って辞職。以来、私立探偵として活動しながら、その事件の真相を追い続けている。最近、ある人物から届いた一通の手紙がきっかけで、今回の集まりに参加することになった。"
    ),
    CharacterTemplate(
        name: "外科医・白鳥 麗子",
        personality: "知性と美貌を兼ね備えた完璧主義者。患者の前では温かく穏やかだが、プライベートでは冷徹な一面を見せる。感情を表に出すことは滅多になく、常に理性的に物事を判断する。しかし、自分の信念に反することに対しては激しい怒りを見せることがある。クラシック音楽を愛し、手術前にはショパンを聴く。",
        background: "国内トップクラスの大学病院で心臓外科のチーフを務める。医学界では天才と呼ばれているが、最近、ある論文のデータ改竄疑惑が持ち上がっている。実家は地方の名士で、莫大な遺産を巡る親族間の争いに巻き込まれている。今回の招待を受けたのは、主催者から「あなたの秘密を知っている」という意味深なメッセージを受け取ったから。"
    ),
    CharacterTemplate(
        name: "記者・鷹野 翔太",
        personality: "正義感が強く、不正を許さない熱血漢。取材対象にはしつこいほど食い下がるが、弱者に対しては驚くほど優しい。口は悪いが裏表がなく、信頼を寄せる人は多い。ただし、スクープのためなら多少の危険を冒すことも厭わず、過去に何度も命を危険にさらしている。酒が入ると饒舌になり、普段は話さない本音を漏らすことがある。",
        background: "全国紙の社会部でエース記者として活躍。政治家の汚職や企業の不正を数多く暴いてきた実績がある。半年前、ある大物政治家の不正を追っていた同僚が不審な事故で亡くなり、その事件の裏に巨大な陰謀があると確信している。今回の集まりの参加者の中に、同僚の死に関わった人物がいるという情報を掴んでいる。"
    ),
    CharacterTemplate(
        name: "令嬢・桜庭 華",
        personality: "華やかな笑顔の裏に鋼の意志を秘めた令嬢。社交界では完璧な立ち居振る舞いで知られるが、実は読書家で、特に推理小説を愛読している。人の感情の機微に敏感で、相手の表情や仕草から心理を読み取る能力に長けている。表向きは従順だが、自分の道は自分で切り開くという強い信念を持っている。",
        background: "桜庭財閥の一人娘として生まれ、幼少期から厳格な教育を受けて育った。父親が急逝した後、若くして財閥の実権を握ることになったが、それを快く思わない親族との権力争いが続いている。最近、父の死が本当に病死だったのか疑問を持ち始め、独自に調査を進めている。今回の集まりは、父と深い関わりがあった人物が主催していると知り、参加を決めた。"
    ),
    CharacterTemplate(
        name: "教授・神谷 一郎",
        personality: "犯罪心理学の権威として名高い学者。温厚で紳士的な物腰だが、犯罪者の心理について語り始めると目の色が変わる。膨大な知識を持ちながらも、常に「自分はまだ何も分かっていない」と謙虚な姿勢を崩さない。しかし、自分の研究テーマに関しては頑固で、一度信じたことは容易に覆さない。パイプを咥えながら思索にふける姿が印象的。",
        background: "東都大学の犯罪心理学教授。30年以上にわたり数百の犯罪事例を分析し、多くの著書を出版してきた。しかし、20年前に関わったプロファイリングが冤罪を生んだ可能性があり、その真相を確かめるために未だ研究を続けている。最近、当時の事件に関する新たな証拠が発見されたという噂を聞きつけ、今回の集まりに参加した。退官間近で、最後の大仕事にしたいと考えている。"
    ),
    CharacterTemplate(
        name: "バーテンダー・蓮",
        personality: "物静かで表情を読ませない男。必要最小限の言葉しか発しないが、その一言一言に重みがある。人の話を聞くのが上手く、常連客からは「懺悔室のようなバー」と呼ばれている。過去に何かを失った影があり、時折遠い目をすることがある。酒の知識は百科事典的で、相手の気分に合わせた一杯を出すのが信条。",
        background: "銀座の路地裏で30年続く老舗バー「月光」のマスター。この街のあらゆる人間の秘密を知っていると噂される存在。実は元公安警察官で、潜入捜査中に起きたある事件をきっかけに警察を去った。その事件で大切な人を失い、以来、表舞台から姿を消してバーテンダーとして生きてきた。今回の集まりの主催者は、彼の過去を知る数少ない人物の一人。"
    ),
    CharacterTemplate(
        name: "画家・藤堂 美月",
        personality: "繊細な感性と爆発的な情熱を併せ持つ芸術家。普段は穏やかで夢見がちだが、創作に関しては妥協を一切許さない。人間の「闇」を描くことに執着し、作品には常にどこか不穏な美しさが漂う。社交的ではないが、一度心を開いた相手には驚くほど率直。感情が昂ると周囲が見えなくなることがある。",
        background: "若くして国際的な美術賞を受賞した天才画家。代表作「深淵」シリーズは、人間の心の闇を描いた衝撃的な作品として世界中で高い評価を受けている。しかし、その作品のモデルとなった人物が一年前に失踪し、警察から参考人として事情聴取を受けた過去がある。最近、失踪した人物から「生きている」というメッセージが届き、その真偽を確かめるために今回の集まりに参加した。"
    ),
    CharacterTemplate(
        name: "実業家・黒崎 剛",
        personality: "カリスマ的なリーダーシップと冷徹な判断力を持つ実業家。部下からの信頼は厚いが、敵には容赦がない。一代で巨大企業グループを築き上げた自負があり、プライドは高い。しかし、家族に対しては不器用な愛情を見せることがある。早朝のランニングを日課とし、どんな時も規律正しい生活を送る。",
        background: "元自衛隊の特殊部隊員。除隊後にセキュリティ会社を起業し、わずか10年で業界最大手に成長させた。政財界に太いパイプを持ち、表に出ない仕事も数多く手がけていると噂される。三年前、最も信頼していたビジネスパートナーが裏切り、会社の機密情報を流出させた事件があった。その裏切り者の行方を追い続けており、今回の集まりにその人物の手がかりがあると睨んでいる。"
    ),
    CharacterTemplate(
        name: "占い師・月影 沙耶",
        personality: "ミステリアスな雰囲気を纏い、予言めいた言葉で周囲を惑わせる。しかし、その神秘的な佇まいの裏には鋭い知性と冷静な分析力が隠されている。人の弱みを見抜く才能があり、それを使って相手をコントロールすることもある。過去のトラウマから夜が苦手で、月明かりの下でしか本当の自分を見せない。",
        background: "テレビや雑誌で引っ張りだこの人気占い師。「予言が当たりすぎる」と評判だが、実際にはその的中率の裏に綿密な調査と心理分析がある。元は大学で心理学を研究していたが、ある実験が倫理問題で打ち切られ、学術界を追われた。占い師としての名声を利用して、かつて自分を追放した人々の秘密を集めている。今回の集まりの参加者の中に、あの実験に関わった人物がいることを知っている。"
    ),
    CharacterTemplate(
        name: "シェフ・火野 龍之介",
        personality: "料理に対する情熱は誰にも負けない完璧主義者。厨房では鬼のように厳しいが、料理を楽しむ客の笑顔を見ると満面の笑みを浮かべる。感情の起伏が激しく、怒ると手がつけられないが、根は純粋で人情味がある。味覚と嗅覚が異常に鋭敏で、料理以外の場面でもその能力が役立つことがある。",
        background: "パリで修業を積み、帰国後に開いたレストランがわずか2年でミシュラン二つ星を獲得した天才シェフ。しかし、その成功の裏で、パリ時代の師匠のレシピを盗んだという告発が持ち上がり、業界を揺るがすスキャンダルとなった。師匠は告発の直後に不審な死を遂げ、事件は未解決のまま。今回の集まりには、パリ時代を知る人物が参加していると聞き、自分の潔白を証明するため、あるいは真相を知るために参加を決意した。"
    ),
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

            HStack(spacing: Spacing.sm) {
                MDButton("🎲 名前だけ", style: .ghost) {
                    withAnimation { characterName = characterTemplates.randomElement()!.name }
                }
                MDButton("🎲 全部おまかせ", style: .ghost) {
                    let t = characterTemplates.randomElement()!
                    withAnimation {
                        characterName = t.name
                        personality = t.personality
                        background = t.background
                    }
                }
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
                withAnimation { personality = characterTemplates.randomElement()!.personality }
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
