import DesignSystem
import SwiftUI

struct IntroView: View {
    @ObservedObject var store: AppStore
    @State private var currentPage = 0
    @State private var selectedPlayer: PlayerInfo?

    private let pageCount = 8

    var body: some View {
        VStack(spacing: 0) {
            pageIndicator

            Group {
                switch currentPage {
                case 0: openingPage
                case 1: victimPage
                case 2: myProfilePage
                case 3: myPublicInfoPage
                case 4: mySecretPage
                case 5: myObjectivePage
                case 6: allCharactersPage
                case 7: readyPage
                default: EmptyView()
                }
            }
            .frame(maxHeight: .infinity)
            .animation(.easeInOut(duration: 0.2), value: currentPage)

            navigationBar
        }
        .background(Color.mdBackground.ignoresSafeArea())
        .sheet(item: $selectedPlayer) { player in
            PlayerDetailSheet(player: player, isMe: player.id == store.room.playerId)
        }
    }

    // MARK: - Navigation

    private var pageIndicator: some View {
        HStack(spacing: 3) {
            ForEach(0..<pageCount, id: \.self) { i in
                Capsule()
                    .fill(i <= currentPage ? Color.mdPrimary : Color.mdTextMuted.opacity(0.3))
                    .frame(width: i == currentPage ? 20 : 6, height: 6)
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

    // MARK: - Page 1: Opening

    private var openingPage: some View {
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
                    Text(setting)
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdTextPrimary)
                        .padding(.horizontal, Spacing.lg)
                }

                if let situation = store.game.scenarioSetting.situation {
                    MDCard {
                        Text(situation)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                    .padding(.horizontal, Spacing.lg)
                }
            }
            .padding(.bottom, Spacing.xl)
        }
    }

    // MARK: - Page 2: Victim

    private var victimPage: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                Text("被害者")
                    .font(.mdLargeTitle)
                    .foregroundStyle(Color.mdAccent)
                    .padding(.top, Spacing.xl)

                if let urlString = store.game.scenarioSetting.victimImageUrl,
                   let url = URL(string: APIClient.defaultBaseURL + urlString) {
                    ZStack {
                        AsyncImage(url: url) { image in
                            image.resizable().aspectRatio(contentMode: .fill)
                        } placeholder: {
                            Image(systemName: "person.slash.fill")
                                .font(.system(size: 60))
                                .foregroundStyle(Color.mdAccent.opacity(0.5))
                        }
                        .frame(width: 120, height: 120)
                        .clipShape(RoundedRectangle(cornerRadius: 12))

                        // Red diagonal line
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.clear)
                            .frame(width: 120, height: 120)
                            .overlay {
                                GeometryReader { geo in
                                    Path { path in
                                        path.move(to: CGPoint(x: geo.size.width, y: 0))
                                        path.addLine(to: CGPoint(x: 0, y: geo.size.height))
                                    }
                                    .stroke(Color.mdAccent, lineWidth: 3)
                                }
                            }
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                } else {
                    Image(systemName: "person.slash.fill")
                        .font(.system(size: 60))
                        .foregroundStyle(Color.mdAccent.opacity(0.5))
                }

                if let name = store.game.scenarioSetting.victimName {
                    Text(name)
                        .font(.mdTitle)
                        .foregroundStyle(Color.mdTextPrimary)
                }

                if let desc = store.game.scenarioSetting.victimDescription {
                    MDCard {
                        Text(desc)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                    .padding(.horizontal, Spacing.lg)
                }
            }
            .padding(.bottom, Spacing.xl)
        }
    }

    // MARK: - Page 3: My Profile

    private var myProfilePage: some View {
        let me = store.room.players.first(where: { $0.id == store.room.playerId })
        return ScrollView {
            VStack(spacing: Spacing.lg) {
                Text("あなたのキャラクター")
                    .font(.mdLargeTitle)
                    .foregroundStyle(Color.mdPrimary)
                    .padding(.top, Spacing.xl)

                if let me {
                    if let urlString = me.portraitUrl,
                       let url = URL(string: APIClient.defaultBaseURL + urlString) {
                        AsyncImage(url: url) { image in
                            image.resizable().aspectRatio(contentMode: .fill)
                        } placeholder: {
                            ProgressView()
                        }
                        .frame(width: 150, height: 150)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                    }

                    Text(me.characterName ?? me.displayName)
                        .font(.mdTitle)
                        .foregroundStyle(Color.mdTextPrimary)

                    profileBasicInfo(me)
                        .padding(.horizontal, Spacing.lg)

                    if let appearance = me.characterAppearance, !appearance.isEmpty {
                        profileCard("外見の特徴", icon: "eye", text: appearance)
                    }

                    if let personality = me.characterPersonality {
                        profileCard("性格", icon: "brain.head.profile", text: personality)
                    }

                    if let background = me.characterBackground {
                        profileCard("経歴", icon: "book", text: background)
                    }
                }
            }
            .padding(.bottom, Spacing.xl)
        }
    }

    // MARK: - Page 4: My Public Info

    private var myPublicInfoPage: some View {
        let me = store.room.players.first(where: { $0.id == store.room.playerId })
        return VStack(spacing: Spacing.lg) {
            Spacer()

            Text("公開情報")
                .font(.mdLargeTitle)
                .foregroundStyle(Color.mdPrimary)

            Text("他のプレイヤーが見れる情報")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)

            if let me {
                MDCard {
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        Text(me.characterName ?? me.displayName)
                            .font(.mdTitle2)
                            .foregroundStyle(Color.mdTextPrimary)

                        HStack(spacing: Spacing.sm) {
                            if let gender = me.characterGender, !gender.isEmpty {
                                profileBadge(gender)
                            }
                            if let age = me.characterAge, !age.isEmpty, age != "不明" {
                                profileBadge("\(age)歳")
                            }
                            if let occupation = me.characterOccupation, !occupation.isEmpty {
                                profileBadge(occupation)
                            }
                        }

                        if let personality = me.characterPersonality {
                            Text(personality)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextSecondary)
                        }
                        if let background = me.characterBackground {
                            Text(background)
                                .font(.mdCaption)
                                .foregroundStyle(Color.mdTextMuted)
                        }
                        if let publicInfo = me.publicInfo, !publicInfo.isEmpty {
                            Divider()
                            VStack(alignment: .leading, spacing: Spacing.xxs) {
                                Text("この集まりでの立場")
                                    .font(.mdCaption)
                                    .foregroundStyle(Color.mdPrimary)
                                Text(publicInfo)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextPrimary)
                            }
                        }
                    }
                }
                .padding(.horizontal, Spacing.lg)

                // Other players' public info
                ForEach(store.room.players.filter { $0.id != store.room.playerId }) { player in
                    if let publicInfo = player.publicInfo, !publicInfo.isEmpty {
                        MDCard {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                Text(player.characterName ?? player.displayName)
                                    .font(.mdHeadline)
                                    .foregroundStyle(Color.mdTextPrimary)
                                Text(publicInfo)
                                    .font(.mdBody)
                                    .foregroundStyle(Color.mdTextSecondary)
                            }
                        }
                        .padding(.horizontal, Spacing.lg)
                    }
                }
            }

            Spacer()
        }
    }

    // MARK: - Page 5: My Secret

    private var mySecretPage: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text("秘密情報")
                .font(.mdLargeTitle)
                .foregroundStyle(Color.mdAccent)

            Text("あなただけが知っている情報")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)

            if let role = store.game.myRole {
                MDCard {
                    HStack {
                        Label("役割", systemImage: "theatermask.and.paintbrush")
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdPrimary)
                        Spacer()
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
                        Label("秘密", systemImage: "lock.fill")
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdAccent)
                        Text(secret)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                }
                .padding(.horizontal, Spacing.lg)
            }

            Spacer()
        }
    }

    // MARK: - Page 6: My Objective

    private var myObjectivePage: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text("あなたの目的")
                .font(.mdLargeTitle)
                .foregroundStyle(Color.mdWarning)

            if let objective = store.game.myObjective {
                MDCard {
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Label("目的", systemImage: "target")
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdWarning)
                        Text(objective)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                }
                .padding(.horizontal, Spacing.lg)
            }

            Text("この目的の達成を目指しながらゲームを進めましょう")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.lg)

            Spacer()
        }
    }

    // MARK: - Page 7: All Characters

    private var allCharactersPage: some View {
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
                        Button { selectedPlayer = player } label: {
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
                                        badge("あなた", color: Color.mdPrimary)
                                    }
                                    if player.isAI {
                                        badge("AI", color: Color.mdInfo)
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

    // MARK: - Page 8: Ready

    private var readyPage: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Image(systemName: "play.circle.fill")
                .font(.system(size: 80))
                .foregroundStyle(Color.mdPrimary)

            Text("準備完了")
                .font(.mdLargeTitle)
                .foregroundStyle(Color.mdPrimary)

            Text("全員の情報を確認しましたか？\nゲームを始めると調査フェーズに入ります。")
                .font(.mdBody)
                .foregroundStyle(Color.mdTextSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.lg)

            Spacer()

            MDButton("ゲームを始める") {
                withAnimation { store.dispatch(.dismissIntro) }
            }
            .padding(.horizontal, Spacing.lg)
            .padding(.bottom, Spacing.md)
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
                avatarPlaceholder
            }
            .frame(width: 50, height: 50)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        } else {
            avatarPlaceholder
        }
    }

    private var avatarPlaceholder: some View {
        Image(systemName: "person.fill")
            .font(.system(size: 20))
            .foregroundStyle(Color.mdTextMuted)
            .frame(width: 50, height: 50)
            .background(Color.mdSurface)
            .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func badge(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.mdCaption2)
            .foregroundStyle(color)
            .padding(.horizontal, Spacing.xs)
            .padding(.vertical, Spacing.xxs)
            .background(color.opacity(0.15))
            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
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

    private func profileBasicInfo(_ player: PlayerInfo) -> some View {
        HStack(spacing: Spacing.sm) {
            if let gender = player.characterGender, !gender.isEmpty {
                profileBadge(gender)
            }
            if let age = player.characterAge, !age.isEmpty, age != "不明" {
                profileBadge("\(age)歳")
            }
            if let occupation = player.characterOccupation, !occupation.isEmpty {
                profileBadge(occupation)
            }
        }
    }

    private func profileBadge(_ text: String) -> some View {
        Text(text)
            .font(.mdCaption)
            .foregroundStyle(Color.mdTextSecondary)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xxs)
            .background(Color.mdSurface)
            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
    }

    private func profileCard(_ label: String, icon: String, text: String) -> some View {
        MDCard {
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Label(label, systemImage: icon)
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdPrimary)
                Text(text)
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextPrimary)
            }
        }
        .padding(.horizontal, Spacing.lg)
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
                    }

                    HStack(spacing: Spacing.sm) {
                        if let gender = player.characterGender, !gender.isEmpty {
                            detailBadge(gender)
                        }
                        if let age = player.characterAge, !age.isEmpty, age != "不明" {
                            detailBadge("\(age)歳")
                        }
                        if let occupation = player.characterOccupation, !occupation.isEmpty {
                            detailBadge(occupation)
                        }
                    }

                    if let appearance = player.characterAppearance, !appearance.isEmpty {
                        detailCard("外見の特徴", icon: "eye", text: appearance)
                    }

                    if let personality = player.characterPersonality {
                        detailCard("性格", icon: "brain.head.profile", text: personality)
                    }

                    if let background = player.characterBackground {
                        detailCard("経歴", icon: "book", text: background)
                    }

                    if let publicInfo = player.publicInfo, !publicInfo.isEmpty {
                        detailCard("この集まりでの立場", icon: "person.2", text: publicInfo)
                    }
                }
                .padding(Spacing.lg)
            }
        }
    }

    private func detailBadge(_ text: String) -> some View {
        Text(text)
            .font(.mdCaption)
            .foregroundStyle(Color.mdTextSecondary)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xxs)
            .background(Color.mdSurface)
            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
    }

    private func detailCard(_ label: String, icon: String, text: String) -> some View {
        MDCard {
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Label(label, systemImage: icon)
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdPrimary)
                Text(text)
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextPrimary)
            }
        }
    }
}
