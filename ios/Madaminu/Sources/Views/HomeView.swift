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
                HStack {
                    Text("マダミヌ")
                        .font(.mdLargeTitle)
                        .foregroundStyle(Color.mdPrimary)
                    Spacer()
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.lg)

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

                HStack(spacing: Spacing.sm) {
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
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.lg)

                ScrollView {
                    LazyVStack(spacing: Spacing.xs) {
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
                                            Text(room.roomCode)
                                                .font(.mdHeadline)
                                                .foregroundStyle(Color.mdPrimary)
                                            if room.hasPassword {
                                                Image(systemName: "lock.fill")
                                                    .font(.mdCaption2)
                                                    .foregroundStyle(Color.mdWarning)
                                            }
                                        }
                                        Text("\(room.hostName ?? "?") のルーム・\(room.playerCount)人")
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
        .task { store.dispatch(.fetchRooms) }
        .sheet(isPresented: $showCreateSheet) {
            CreateRoomSheet(store: store, isPresented: $showCreateSheet)
        }
        .sheet(isPresented: $showJoinSheet) {
            JoinRoomSheet(store: store, isPresented: $showJoinSheet, joinCode: $joinCode, password: $password)
        }
    }
}

// MARK: - Create Room Sheet

struct CreateRoomSheet: View {
    @ObservedObject var store: AppStore
    @Binding var isPresented: Bool
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
                    store.dispatch(.createRoom(password: usePassword ? password : nil))
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

            VStack(spacing: Spacing.md) {
                ProgressView()
                    .tint(Color.mdPrimary)
                    .scaleEffect(1.5)

                Text(store.room.progressMessage ?? "シナリオを生成中...")
                    .font(.mdBody)
                    .foregroundStyle(Color.mdTextSecondary)

                if let error = store.errorMessage {
                    Text(error)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdError)
                }
            }
        }
        .task {
            await store.setupSpeech()
        }
    }
}
