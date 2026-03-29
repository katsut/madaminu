import DesignSystem
import SwiftUI

public struct HomeView: View {
    @StateObject private var store = AppStore()

    public init() {}

    public var body: some View {
        ZStack {
            switch store.screen {
            case .home:
                HomeScreen(store: store)
            case .lobby:
                RoomLobbyView(store: store)
            case .characterCreation:
                CharacterCreationView(store: store)
            case .generating:
                GeneratingView(store: store)
            case .intro:
                IntroView(store: store)
            case .playing:
                GamePlayView(store: store)
            case .ended:
                GamePlayView(store: store)
            }
        }
        .animation(.easeInOut(duration: 0.3), value: store.screen)
    }
}

// MARK: - Home Screen

struct HomeScreen: View {
    @ObservedObject var store: AppStore
    @State private var showCreateSheet = false
    @State private var showJoinSheet = false
    @State private var joinCode = ""
    @State private var password = ""

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Title logo with text overlay
                if let logoImage = UIImage(named: "logo", in: .module, compatibleWith: nil) {
                    Image(uiImage: logoImage)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                        .frame(height: 200)
                        .clipped()
                        .overlay(
                            LinearGradient(
                                colors: [Color.clear, Color.mdBackground],
                                startPoint: .center,
                                endPoint: .bottom
                            )
                        )
                        .overlay(
                            VStack(spacing: 4) {
                                Text("マダ見ヌ")
                                    .font(.custom("HiraMinProN-W6", size: 40))
                                    .tracking(8)
                                    .foregroundStyle(Color(red: 0.9, green: 0.2, blue: 0.15))
                                    .shadow(color: .black, radius: 6, x: 0, y: 3)
                                    .shadow(color: .red.opacity(0.3), radius: 12, x: 0, y: 0)
                                Text("〜まだ誰も見たことのないミステリー〜")
                                    .font(.custom("HiraMinProN-W3", size: 12))
                                    .foregroundStyle(Color(red: 0.8, green: 0.7, blue: 0.55))
                                    .shadow(color: .black.opacity(0.8), radius: 3, x: 0, y: 1)
                            }
                            .padding(.top, 20)
                        )
                }

                MDTextField(label: "あなたの名前", text: Binding(
                    get: { store.room.displayName },
                    set: { store.room.displayName = $0 }
                ), placeholder: "名前を入力")
                    .padding(.horizontal, Spacing.lg)
                    .padding(.top, Spacing.md)

                if let error = store.errorMessage {
                    Text(error)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdError)
                        .padding(.horizontal, Spacing.lg)
                        .padding(.top, Spacing.xs)
                }

                ScrollView {
                    LazyVStack(spacing: Spacing.xs) {
                        if !store.room.myRooms.isEmpty {
                            HStack {
                                Text("自分のルーム")
                                    .font(.mdHeadline)
                                    .foregroundStyle(Color.mdTextSecondary)
                                Spacer()
                            }
                            .padding(.top, Spacing.sm)

                            ForEach(store.room.myRooms) { myRoom in
                                MDCard {
                                    HStack {
                                        VStack(alignment: .leading, spacing: Spacing.xxs) {
                                            HStack(spacing: Spacing.xs) {
                                                Text(myRoom.roomCode)
                                                    .font(.mdHeadline)
                                                    .foregroundStyle(Color.mdPrimary)
                                                Text(statusLabel(myRoom.status))
                                                    .font(.mdCaption2)
                                                    .foregroundStyle(statusColor(myRoom.status))
                                                    .padding(.horizontal, Spacing.xs)
                                                    .padding(.vertical, 2)
                                                    .background(statusColor(myRoom.status).opacity(0.15))
                                                    .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                            }
                                            Text(myRoom.characterName ?? myRoom.displayName)
                                                .font(.mdCaption)
                                                .foregroundStyle(Color.mdTextSecondary)
                                        }
                                        Spacer()
                                        if myRoom.status != "ended" {
                                            MDButton(myRoom.status == "waiting" ? "再接続" : "復帰", style: .secondary) {
                                                store.dispatch(.rejoinRoom(
                                                    sessionToken: myRoom.sessionToken,
                                                    playerId: myRoom.playerId,
                                                    roomCode: myRoom.roomCode,
                                                    status: myRoom.status
                                                ))
                                            }
                                        }
                                        if myRoom.isHost {
                                            Button {
                                                store.dispatch(.deleteRoom(roomCode: myRoom.roomCode))
                                            } label: {
                                                Image(systemName: "trash")
                                                    .foregroundStyle(Color.mdError)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        HStack {
                            Text("ルーム一覧")
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdTextSecondary)
                            Spacer()
                            Button {
                                store.dispatch(.fetchRooms)
                            } label: {
                                Image(systemName: "arrow.clockwise")
                                    .foregroundStyle(Color.mdTextMuted)
                            }
                        }
                        .padding(.top, Spacing.sm)

                        if store.room.availableRooms.isEmpty {
                            Text("ルームがありません")
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextMuted)
                                .padding(Spacing.xl)
                        }

                        ForEach(store.room.availableRooms) { room in
                            MDCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: Spacing.xxs) {
                                        HStack(spacing: Spacing.xs) {
                                            Text(room.roomName ?? room.roomCode)
                                                .font(.mdHeadline)
                                                .foregroundStyle(Color.mdPrimary)
                                            if room.hasPassword {
                                                Image(systemName: "lock.fill")
                                                    .font(.mdCaption2)
                                                    .foregroundStyle(Color.mdWarning)
                                            }
                                        }
                                        Text("\(room.hostName ?? "?") のルーム・\(room.playerCount)人・\(room.roomCode)")
                                            .font(.mdCaption)
                                            .foregroundStyle(Color.mdTextSecondary)
                                    }
                                    Spacer()
                                    MDButton("参加", style: .secondary) {
                                        store.dispatch(.joinRoom(code: room.roomCode, password: nil))
                                    }
                                }
                            }
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                    .padding(.top, Spacing.xs)
                }

                HStack(spacing: Spacing.sm) {
                    MDButton("ルームを作成") {
                        showCreateSheet = true
                    }
                    MDButton("コードで参加", style: .secondary) {
                        showJoinSheet = true
                    }
                }
                .padding(Spacing.lg)
            }
        }
        .onTapGesture {
            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
        }
        .task {
            store.dispatch(.fetchRooms)
            store.dispatch(.fetchMyRooms)
            while store.screen == .home {
                try? await Task.sleep(for: .seconds(5))
                store.dispatch(.fetchRooms)
            }
        }
        .sheet(isPresented: $showCreateSheet) {
            CreateRoomSheet(store: store, isPresented: $showCreateSheet)
        }
        .sheet(isPresented: $showJoinSheet) {
            JoinRoomSheet(store: store, isPresented: $showJoinSheet, joinCode: $joinCode, password: $password)
        }
    }

    private func statusLabel(_ status: String) -> String {
        switch status {
        case "waiting": "待機中"
        case "generating": "生成中"
        case "playing": "プレイ中"
        case "voting": "投票中"
        case "ended": "終了"
        default: status
        }
    }

    private func statusColor(_ status: String) -> Color {
        switch status {
        case "waiting": Color.mdInfo
        case "generating", "playing", "voting": Color.mdPrimary
        case "ended": Color.mdTextMuted
        default: Color.mdTextMuted
        }
    }
}

// MARK: - Create Room Sheet

struct CreateRoomSheet: View {
    @ObservedObject var store: AppStore
    @Binding var isPresented: Bool
    @State private var roomName = ""
    @State private var usePassword = false
    @State private var password = ""

    var body: some View {
        ZStack {
            Color.mdBackground.ignoresSafeArea()

            VStack(spacing: Spacing.md) {
                HStack {
                    Text("ルーム作成")
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdPrimary)
                    Spacer()
                    Button { isPresented = false } label: {
                        Image(systemName: "xmark").foregroundStyle(Color.mdTextSecondary)
                    }
                }

                MDTextField(label: "ルーム名（任意）", text: $roomName, placeholder: "例: 週末ミステリー会")

                Toggle(isOn: $usePassword) {
                    Label("パスワードを設定", systemImage: "lock")
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)
                }
                .tint(Color.mdPrimary)

                if usePassword {
                    MDTextField(label: "パスワード", text: $password, placeholder: "パスワードを入力")
                }

                Spacer()

                MDButton("作成", isLoading: store.isLoading) {
                    store.dispatch(.createRoom(
                        roomName: roomName.isEmpty ? nil : roomName,
                        password: usePassword ? password : nil
                    ))
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        if store.screen == .lobby { isPresented = false }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }
}

// MARK: - Join Room Sheet

struct JoinRoomSheet: View {
    @ObservedObject var store: AppStore
    @Binding var isPresented: Bool
    @Binding var joinCode: String
    @Binding var password: String

    var body: some View {
        ZStack {
            Color.mdBackground.ignoresSafeArea()

            VStack(spacing: Spacing.md) {
                HStack {
                    Text("ルームに参加")
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdPrimary)
                    Spacer()
                    Button { isPresented = false } label: {
                        Image(systemName: "xmark").foregroundStyle(Color.mdTextSecondary)
                    }
                }

                MDTextField(label: "参加コード", text: $joinCode, placeholder: "6文字のコード")
                MDTextField(label: "パスワード（任意）", text: $password, placeholder: "パスワード")

                Spacer()

                MDButton("参加する", isLoading: store.isLoading) {
                    store.dispatch(.joinRoom(code: joinCode, password: password.isEmpty ? nil : password))
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        if store.screen == .lobby { isPresented = false }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }
}

// MARK: - Generating View

struct GeneratingView: View {
    @ObservedObject var store: AppStore

    var body: some View {
        ZStack {
            Color.mdBackground.ignoresSafeArea()

            VStack(alignment: .leading, spacing: Spacing.lg) {
                HStack {
                    Button { store.dispatch(.leaveRoom) } label: {
                        HStack(spacing: Spacing.xxs) {
                            Image(systemName: "chevron.left")
                            Text("退出")
                        }
                        .font(.mdCallout)
                        .foregroundStyle(Color.mdTextSecondary)
                    }
                    Spacer()
                }

                Spacer()

                Text("ゲームを準備中")
                    .font(.mdTitle)
                    .foregroundStyle(Color.mdPrimary)
                    .frame(maxWidth: .infinity, alignment: .center)

                VStack(alignment: .leading, spacing: Spacing.md) {
                    checkItem("AIプレイヤーの補充", done: store.game.aiPlayersReady)
                    checkItem("シナリオの生成", done: store.game.scenarioReady)
                    checkItem("舞台画像の生成", done: store.game.sceneImageReady)
                    checkItem("キャラクター画像の生成", done: store.game.portraitsReady)
                    checkItem("ゲームの準備完了", done: store.game.allReady)
                }
                .padding(Spacing.lg)

                if !store.game.allReady {
                    ProgressView()
                        .tint(Color.mdPrimary)
                        .frame(maxWidth: .infinity, alignment: .center)
                }

                VStack(alignment: .leading, spacing: Spacing.sm) {
                    Text("もうすぐストーリーが始まります")
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdTextPrimary)

                    guideStep(1, "物語の設定と自分のプロフィール・目的を読む")
                    guideStep(2, "他のプレイヤーのプロフィールを確認する")
                    guideStep(3, "手帳に配られた証拠・アリバイを確認する")
                    guideStep(4, "調査計画で最初に調べる場所をみんなで決める")
                }
                .padding(Spacing.lg)
                .background(Color.mdSurface)
                .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))

                if let error = store.errorMessage {
                    Text(error)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdError)
                        .frame(maxWidth: .infinity, alignment: .center)
                }

                Spacer()
            }
            .padding(Spacing.lg)
        }
        .task {
            await store.setupSpeech()
        }
    }

    private func checkItem(_ label: String, done: Bool) -> some View {
        HStack(spacing: Spacing.sm) {
            Image(systemName: done ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(done ? Color.mdSuccess : Color.mdTextMuted)
                .font(.mdTitle2)

            Text(label)
                .font(.mdBody)
                .foregroundStyle(done ? Color.mdTextPrimary : Color.mdTextSecondary)
        }
    }

    private func guideStep(_ number: Int, _ text: String) -> some View {
        HStack(alignment: .top, spacing: Spacing.sm) {
            Text("\(number).")
                .font(.mdHeadline)
                .foregroundStyle(Color.mdPrimary)
                .frame(width: 20)
            Text(text)
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextSecondary)
        }
    }
}
