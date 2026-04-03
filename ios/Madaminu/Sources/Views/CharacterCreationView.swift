import DesignSystem
import SwiftUI

private struct CharacterTemplate {
    let name: String
    let nameKana: String
    let gender: String
    let age: String
    let occupation: String
    let appearance: String
    let personality: String
    let background: String
}

private let characterTemplates: [CharacterTemplate] = [
    // --- 定番キャラクター ---
    CharacterTemplate(
        name: "明智 小五郎",
        nameKana: "あけち こごろう",
        gender: "男",
        age: "45",
        occupation: "私立探偵",
        appearance: "鋭い目つきで、常にトレンチコートを羽織っている。",
        personality: "鋭い観察眼と論理的思考の持ち主。飄々としているが、事件の核心に迫ると表情が一変する。",
        background: "警視庁捜査一課の元エース刑事。10年前に担当した事件で無実の人間を追い詰めた過去があり、辞職して私立探偵に。"
    ),
    CharacterTemplate(
        name: "白鳥 麗子",
        nameKana: "しらとり れいこ",
        gender: "女",
        age: "38",
        occupation: "心臓外科医",
        appearance: "知性と美貌を兼ね備え、常に白衣を着こなしている。",
        personality: "完璧主義者。患者の前では温かく穏やかだが、プライベートでは冷徹な一面を見せる。",
        background: "国内トップクラスの大学病院でチーフを務める。最近、論文のデータ改竄疑惑が持ち上がっている。"
    ),
    CharacterTemplate(
        name: "鷹野 翔太",
        nameKana: "たかの しょうた",
        gender: "男",
        age: "32",
        occupation: "新聞記者",
        appearance: "常にメモ帳を持ち歩き、髪はいつも少し乱れている。",
        personality: "正義感が強く、不正を許さない熱血漢。口は悪いが裏表がない。",
        background: "全国紙の社会部エース記者。半年前、同僚が不審な事故で亡くなり、その裏に陰謀があると確信している。"
    ),
    CharacterTemplate(
        name: "桜庭 華",
        nameKana: "さくらば はな",
        gender: "女",
        age: "26",
        occupation: "財閥令嬢",
        appearance: "華やかなドレスに身を包み、品のある佇まい。",
        personality: "華やかな笑顔の裏に鋼の意志を秘めた令嬢。相手の心理を読み取る能力に長けている。",
        background: "桜庭財閥の一人娘。父親が急逝した後、若くして実権を握った。父の死が本当に病死だったのか疑問を持っている。"
    ),
    CharacterTemplate(
        name: "神谷 一郎",
        nameKana: "かみや いちろう",
        gender: "男",
        age: "62",
        occupation: "大学教授",
        appearance: "白髪交じりの髪に銀縁眼鏡。パイプを咥えている。",
        personality: "犯罪心理学の権威。温厚で紳士的だが、研究テーマに関しては頑固。",
        background: "東都大学の犯罪心理学教授。30年以上犯罪事例を分析。退官間近で最後の大仕事にしたいと考えている。"
    ),
    CharacterTemplate(
        name: "蓮",
        nameKana: "れん",
        gender: "男",
        age: "50",
        occupation: "バーテンダー",
        appearance: "物静かで表情を読ませない。整った身なりで清潔感がある。",
        personality: "必要最小限の言葉しか発しないが、その一言一言に重みがある。聞き上手。",
        background: "銀座の老舗バーのマスター。実は元公安警察官で、潜入捜査中の事件をきっかけに警察を去った。"
    ),
    CharacterTemplate(
        name: "藤堂 美月",
        nameKana: "とうどう みづき",
        gender: "女",
        age: "29",
        occupation: "画家",
        appearance: "繊細な雰囲気で、指先に絵の具の跡が残っている。",
        personality: "繊細な感性と爆発的な情熱を併せ持つ芸術家。人間の「闇」を描くことに執着している。",
        background: "若くして国際的な美術賞を受賞。代表作のモデルが一年前に失踪し、参考人として事情聴取を受けた。"
    ),
    CharacterTemplate(
        name: "黒崎 剛",
        nameKana: "くろさき つよし",
        gender: "男",
        age: "47",
        occupation: "セキュリティ会社社長",
        appearance: "がっしりした体格。鋭い目つきで威圧感がある。",
        personality: "カリスマ的なリーダーシップと冷徹な判断力。部下からの信頼は厚いが、敵には容赦がない。",
        background: "元自衛隊の特殊部隊員。除隊後にセキュリティ会社を起業し、10年で業界最大手に成長させた。"
    ),
    CharacterTemplate(
        name: "月影 沙耶",
        nameKana: "つきかげ さや",
        gender: "女",
        age: "35",
        occupation: "占い師",
        appearance: "ミステリアスな雰囲気。大きなイヤリングと深い紫色の衣装。",
        personality: "神秘的な佇まいの裏に鋭い知性と冷静な分析力。人の弱みを見抜く才能がある。",
        background: "テレビで人気の占い師。元は大学で心理学を研究していたが、倫理問題で学術界を追われた。"
    ),
    CharacterTemplate(
        name: "火野 龍之介",
        nameKana: "ひの りゅうのすけ",
        gender: "男",
        age: "40",
        occupation: "シェフ",
        appearance: "大柄で力強い体格。情熱的な目をしている。",
        personality: "料理に対する情熱は誰にも負けない完璧主義者。感情の起伏が激しいが根は純粋。",
        background: "パリで修業後、帰国して開いたレストランがミシュラン二つ星を獲得。師匠のレシピを盗んだという告発がある。"
    ),

    // --- 追加キャラクター ---
    CharacterTemplate(
        name: "氷室 凛",
        nameKana: "ひむろ りん",
        gender: "女",
        age: "42",
        occupation: "検事",
        appearance: "隙のないスーツ姿。冷たい美貌と鋭い眼光。",
        personality: "感情を表に出さない氷の女。正義のためなら手段を選ばない。しかし弱者への共感は深い。",
        background: "有罪率99.9%を誇る敏腕検事。5年前に無罪判決を出した唯一の事件が未解決のまま心に引っかかっている。"
    ),
    CharacterTemplate(
        name: "九条 誠",
        nameKana: "くじょう まこと",
        gender: "男",
        age: "55",
        occupation: "政治家",
        appearance: "堂々とした体躯にオーダーメイドのスーツ。白髪が渋みを添える。",
        personality: "カリスマ的な弁舌と圧倒的な存在感。裏では冷酷な計算をしている。",
        background: "与党の重鎮で次期首相候補。クリーンなイメージだが、秘書が横領で逮捕された過去がある。"
    ),
    CharacterTemplate(
        name: "綾瀬 千尋",
        nameKana: "あやせ ちひろ",
        gender: "女",
        age: "24",
        occupation: "ハッカー",
        appearance: "パーカーにジーンズ。ノートPCを常に持ち歩いている。目の下にクマ。",
        personality: "天才的なIT技術を持つが社交性は皆無。ネット上では饒舌だが対面では極度に人見知り。",
        background: "元ホワイトハッカー。大手企業のセキュリティ診断で名を上げたが、ある事件でブラックリスト入りした。"
    ),
    CharacterTemplate(
        name: "東郷 義男",
        nameKana: "とうごう よしお",
        gender: "男",
        age: "70",
        occupation: "元軍人",
        appearance: "背筋がぴんと伸びた老紳士。左手に古い傷跡がある。",
        personality: "寡黙で規律正しい。若い世代には厳しいが面倒見がよい。嘘をつけない性格。",
        background: "自衛隊で40年務め上げた元陸将補。退役後は静かに暮らしていたが、旧友の不審死をきっかけに再び動き出す。"
    ),
    CharacterTemplate(
        name: "真白 あおい",
        nameKana: "ましろ あおい",
        gender: "女",
        age: "19",
        occupation: "大学生",
        appearance: "明るい茶髪に大きなリュック。いつもイヤホンをしている。",
        personality: "好奇心旺盛で怖いもの知らず。空気を読まない発言が結果的に核心を突くことがある。",
        background: "法学部の1年生。推理小説オタクで、本物の事件に遭遇して大興奮している。実はある財界人の隠し子。"
    ),
    CharacterTemplate(
        name: "朱鷺沢 響",
        nameKana: "ときざわ ひびき",
        gender: "男",
        age: "28",
        occupation: "ミュージシャン",
        appearance: "長髪を後ろで束ねている。指は細く長い。革ジャンに銀のアクセサリー。",
        personality: "自由奔放で掴みどころがない。人の感情を音で表現できると豪語する天才肌。",
        background: "インディーズバンドのボーカル。突然メジャーデビューが決まったが、作詞のネタ元に盗作疑惑。"
    ),
    CharacterTemplate(
        name: "柊 雪乃",
        nameKana: "ひいらぎ ゆきの",
        gender: "女",
        age: "45",
        occupation: "旅館女将",
        appearance: "きちんとした和装。柔らかな笑顔だが目は笑っていない。",
        personality: "おもてなしの鬼。表面は穏やかだが、旅館を守るためなら何でもする覚悟がある。",
        background: "老舗温泉旅館の三代目女将。経営難に陥った旅館を立て直した実力者。先代の死に不審な点がある。"
    ),
    CharacterTemplate(
        name: "獅子堂 拓海",
        nameKana: "ししどう たくみ",
        gender: "男",
        age: "36",
        occupation: "弁護士",
        appearance: "高級スーツに派手なネクタイ。自信に満ちた笑顔。",
        personality: "負けず嫌いで弁が立つ。クライアントのためなら法の抜け穴も厭わない。正義より勝利を優先する。",
        background: "勝率98%の敏腕弁護士。最近の大型訴訟で裏取引をした噂がある。"
    ),
    CharacterTemplate(
        name: "天草 美咲",
        nameKana: "あまくさ みさき",
        gender: "女",
        age: "31",
        occupation: "考古学者",
        appearance: "日焼けした肌にカーゴパンツ。首から古いペンダントを下げている。",
        personality: "冒険好きで行動力がある。学術的な議論になると誰よりも熱くなる。直感で動くタイプ。",
        background: "古代文明の研究者。最近の発掘で歴史を覆す遺物を見つけたが、その真偽を巡って学会が紛糾している。"
    ),
    CharacterTemplate(
        name: "霧島 悠人",
        nameKana: "きりしま ゆうと",
        gender: "男",
        age: "22",
        occupation: "プロゲーマー",
        appearance: "細身でゲーミングチェアに座り慣れた姿勢。目つきは鋭い。",
        personality: "反射神経と状況判断は超一流。ゲームの外でも人の行動パターンを読むのが得意。",
        background: "世界大会で優勝したeスポーツ選手。最近スポンサーとの契約トラブルで精神的に追い詰められている。"
    ),
    CharacterTemplate(
        name: "如月 操",
        nameKana: "きさらぎ みさお",
        gender: "女",
        age: "33",
        occupation: "葬儀屋",
        appearance: "黒のワンピースに白い手袋。常に落ち着いた物腰。",
        personality: "死に慣れている独特の死生観を持つ。穏やかだが時々ぞっとするほど冷静なことを言う。",
        background: "家業の葬儀社を継いだ三代目。最近、不自然な死に方をした遺体が立て続けに運び込まれている。"
    ),
    CharacterTemplate(
        name: "鳳 龍太郎",
        nameKana: "おおとり りゅうたろう",
        gender: "男",
        age: "58",
        occupation: "映画監督",
        appearance: "ベレー帽にサングラス。常に葉巻を持っている。大げさな身振り。",
        personality: "芸術至上主義の天才肌。自分の作品のためなら人の気持ちを平気で踏みにじる傲慢さがある。",
        background: "国際映画祭で最高賞を3度受賞した巨匠。次回作の主演俳優が撮影中に怪死した。"
    ),
    CharacterTemplate(
        name: "雨宮 紬",
        nameKana: "あまみや つむぎ",
        gender: "女",
        age: "27",
        occupation: "図書館司書",
        appearance: "地味なカーディガンに眼鏡。いつも本を抱えている。声が小さい。",
        personality: "内向的で目立つことを嫌うが、記憶力は驚異的。一度読んだ本の内容を完全に覚えている。",
        background: "古い図書館で働く司書。禁帯出の古文書の中に、この街の有力者たちの秘密が記された手記を見つけてしまった。"
    ),
    CharacterTemplate(
        name: "烏丸 京介",
        nameKana: "からすま きょうすけ",
        gender: "男",
        age: "44",
        occupation: "骨董商",
        appearance: "着物姿で飄々とした風貌。右目にモノクルをかけている。",
        personality: "掴みどころのない食わせ者。真贋を見抜く眼力は本物だが、自身の言葉の真偽は誰にもわからない。",
        background: "裏社会にもコネを持つ骨董商。最近、曰く付きの美術品の取引に関わっている。"
    ),
    CharacterTemplate(
        name: "花園 ルカ",
        nameKana: "はなぞの るか",
        gender: "不明",
        age: "20",
        occupation: "アイドル",
        appearance: "中性的な美貌。ステージ衣装のまま現れることが多い。",
        personality: "ファンの前では完璧な笑顔。しかし素顔は繊細で孤独。本当の自分を誰にも見せられない。",
        background: "国民的アイドルグループのセンター。急な活動休止発表の裏に何かがあると噂されている。"
    ),
    CharacterTemplate(
        name: "鬼頭 源蔵",
        nameKana: "きとう げんぞう",
        gender: "男",
        age: "68",
        occupation: "漁師",
        appearance: "海風で日焼けした顔。太い腕と大きな手。素朴な作業着。",
        personality: "頑固で口下手だが、海と人を愛する男。嘘を嫌い、思ったことをそのまま口にする。",
        background: "50年間漁師一筋。最近、近海で密漁船を目撃した。通報したが何故か警察は動かない。"
    ),
    CharacterTemplate(
        name: "九十九 蘭",
        nameKana: "つくも らん",
        gender: "女",
        age: "52",
        occupation: "毒物学者",
        appearance: "白衣の下に派手な花柄ワンピース。ゴム手袋が手放せない。",
        personality: "毒物への愛が深すぎて周囲を引かせる。明るく社交的だが、会話の端々に不穏な知識が混じる。",
        background: "大学の毒物学研究室の主任。自宅に世界中の毒のコレクションがある。「研究用です」が口癖。"
    ),
    CharacterTemplate(
        name: "影山 透",
        nameKana: "かげやま とおる",
        gender: "男",
        age: "39",
        occupation: "マジシャン",
        appearance: "シルクハットにマント。常に手袋をしている。どこからともなくカードを出す。",
        personality: "人を欺くことに美学を持つ。嘘と真実の境界を曖昧にするのが得意。",
        background: "世界的に有名なイリュージョニスト。アシスタントが公演中に本当に消えた事件の真相を知っている。"
    ),
    CharacterTemplate(
        name: "瀬戸内 小梅",
        nameKana: "せとうち こうめ",
        gender: "女",
        age: "78",
        occupation: "元スパイ",
        appearance: "上品な老婦人。杖をついているが足取りは確か。パールのネックレス。",
        personality: "穏やかなおばあちゃんに見えるが、目の奥に鋭さが宿っている。紅茶を淹れながら相手の秘密を引き出す。",
        background: "冷戦時代に某国の諜報機関で活動していた。引退して30年、過去を知る者が次々と消えている。"
    ),
    CharacterTemplate(
        name: "日向 陽",
        nameKana: "ひなた よう",
        gender: "男",
        age: "16",
        occupation: "高校生探偵",
        appearance: "学ランにスニーカー。好奇心に満ちた大きな目。ポケットに虫眼鏡。",
        personality: "天真爛漫で恐れを知らない。大人が見落とすことに気づく鋭さがある。少し生意気。",
        background: "地元で3件の事件を解決した噂の高校生。今回の事件現場にたまたま居合わせた…はずだった。"
    ),

    // --- おふざけ・変わり種キャラクター ---
    CharacterTemplate(
        name: "ポチ三世",
        nameKana: "ぽちさんせい",
        gender: "不明",
        age: "7",
        occupation: "名探偵犬",
        appearance: "ゴールデンレトリバー。赤い蝶ネクタイと小さな探偵帽。賢そうな目。",
        personality: "ワンワンとしか言わないが、なぜか的確に犯人を見つけ出す。おやつで買収される弱点あり。",
        background: "警察犬訓練校を首席で卒業した天才犬。嗅覚で嘘を見抜くという都市伝説がある。前の飼い主は行方不明。"
    ),
    CharacterTemplate(
        name: "AZ-09",
        nameKana: "えーぜっと ぜろきゅう",
        gender: "不明",
        age: "3",
        occupation: "家庭用アンドロイド",
        appearance: "人間そっくりだが瞳がわずかに青く光る。常にスーツを着用。動きがやや機械的。",
        personality: "論理的すぎて空気が読めない。感情を理解しようとするが、的外れな共感を見せる。",
        background: "最新型AIアンドロイド。被害者の家で使用人として働いていた。事件当日のログが一部消去されている。"
    ),
    CharacterTemplate(
        name: "ぬらりひょん太郎",
        nameKana: "ぬらりひょんたろう",
        gender: "男",
        age: "800",
        occupation: "妖怪の総大将",
        appearance: "巨大な頭に和装。いつの間にか隣に座っている。存在感があるようでない。",
        personality: "飄々として何を考えているかわからない。人間社会に溶け込みすぎて妖怪仲間に怒られている。",
        background: "数百年にわたり人間を観察してきた妖怪のトップ。最近はSNSにハマっている。人間の殺し合いには興味がないはずだが…"
    ),
    CharacterTemplate(
        name: "デス山田 太郎",
        nameKana: "ですやまだ たろう",
        gender: "男",
        age: "35",
        occupation: "自称・死神",
        appearance: "真っ黒なローブに大鎌…と思いきやスーツ姿にネクタイ。鎌は折りたたみ傘。",
        personality: "中二病をこじらせたまま大人になった。本人は本気で死神だと信じている。意外と常識人。",
        background: "市役所の戸籍課に勤務。「死亡届を毎日扱うので死神の資格がある」が持論。趣味はミステリー小説収集。"
    ),
    CharacterTemplate(
        name: "もち丸",
        nameKana: "もちまる",
        gender: "不明",
        age: "不明",
        occupation: "謎の生き物",
        appearance: "白くて丸い。大福のような見た目。目がつぶらで可愛い。二足歩行する。",
        personality: "「もち」としか言わないが、表情豊かで感情は伝わる。なぜかいつも事件現場にいる。",
        background: "どこから来たのか誰も知らない謎の存在。被害者が最後に目撃したのはこの生き物だったという証言がある。"
    ),
]

struct CharacterCreationView: View {
    @ObservedObject var store: AppStore
    @State private var currentStep = 0
    @State private var characterName = ""
    @State private var gender = "不明"
    @State private var nameKana = ""
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
            MDTextField(label: "キャラクター名", text: $characterName, placeholder: "例: 明智 小五郎")
            MDTextField(label: "読み仮名", text: $nameKana, placeholder: "例: あけち こごろう")

            HStack(spacing: Spacing.sm) {
                MDButton("🎲 名前だけ", style: .ghost) {
                    let t = characterTemplates.randomElement()!
                    withAnimation {
                        characterName = t.name
                        nameKana = t.nameKana
                    }
                }
                MDButton("🎲 全部おまかせ", style: .ghost) {
                    let t = characterTemplates.randomElement()!
                    withAnimation {
                        characterName = t.name
                        nameKana = t.nameKana
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
                HStack(spacing: Spacing.xs) {
                    Image(systemName: "info.circle")
                        .foregroundStyle(Color.mdInfo)
                    Text("作成後、AIによるプロフィールの調整が入る場合があります")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextMuted)
                }
            }

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
                        nameKana: nameKana,
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
