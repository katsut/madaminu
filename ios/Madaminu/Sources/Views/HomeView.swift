import DesignSystem
import SwiftUI

public struct HomeView: View {
    @State private var viewModel = RoomViewModel()
    @State private var showJoinSheet = false
    @State private var showCreateSheet = false
    @State private var joinPassword = ""
    @State private var joiningRoomCode: String?

    public init() {}

    public var body: some View {
        if viewModel.isGameStarted, let pid = viewModel.playerId, let token = viewModel.sessionToken {
            GamePlayView(viewModel: GameViewModel(
                roomCode: viewModel.roomCode,
                playerId: pid,
                sessionToken: token,
                isHost: viewModel.isHost
            ))
        } else if viewModel.isInRoom {
            RoomLobbyView(viewModel: viewModel)
        } else {
            homeContent
        }
    }

    private var homeContent: some View {
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

                MDTextField(label: "あなたの名前", text: $viewModel.displayName, placeholder: "名前を入力")
                    .padding(.horizontal, Spacing.lg)
                    .padding(.top, Spacing.md)

                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdError)
                        .padding(.horizontal, Spacing.lg)
                }

                HStack(spacing: Spacing.sm) {
                    Text("ルーム一覧")
                        .font(.mdHeadline)
                        .foregroundStyle(Color.mdTextSecondary)
                    Spacer()
                    Button {
                        Task { await viewModel.fetchRooms() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .foregroundStyle(Color.mdTextMuted)
                    }
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.lg)

                ScrollView {
                    LazyVStack(spacing: Spacing.xs) {
                        if viewModel.availableRooms.isEmpty {
                            Text("ルームがありません")
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextMuted)
                                .padding(Spacing.xl)
                        }

                        ForEach(viewModel.availableRooms) { room in
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
                                        if room.hasPassword {
                                            joiningRoomCode = room.roomCode
                                            joinPassword = ""
                                            showJoinSheet = true
                                        } else {
                                            Task { await viewModel.joinFromList(roomCode: room.roomCode) }
                                        }
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
                        joiningRoomCode = nil
                    }
                }
                .padding(Spacing.lg)
            }
        }
        .onTapGesture {
            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
        }
        .task {
            await viewModel.fetchRooms()
        }
        .sheet(isPresented: $showCreateSheet) {
            CreateRoomSheet(viewModel: viewModel, isPresented: $showCreateSheet)
        }
        .sheet(isPresented: $showJoinSheet) {
            JoinRoomSheet(viewModel: viewModel, isPresented: $showJoinSheet)
        }
    }
}

struct CreateRoomSheet: View {
    @Bindable var viewModel: RoomViewModel
    @Binding var isPresented: Bool
    @State private var usePassword = false

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.md) {
                HStack {
                    Text("ルーム作成")
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdPrimary)
                    Spacer()
                    Button { isPresented = false } label: {
                        Image(systemName: "xmark")
                            .foregroundStyle(Color.mdTextSecondary)
                    }
                }

                Toggle(isOn: $usePassword) {
                    Label("パスワードを設定", systemImage: "lock")
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextPrimary)
                }
                .tint(Color.mdPrimary)

                if usePassword {
                    MDTextField(label: "パスワード", text: $viewModel.password, placeholder: "パスワードを入力")
                }

                Spacer()

                MDButton("作成", isLoading: viewModel.isLoading) {
                    Task {
                        await viewModel.createRoom()
                        if viewModel.isInRoom { isPresented = false }
                    }
                }
            }
            .padding(Spacing.lg)
        }
    }
}
