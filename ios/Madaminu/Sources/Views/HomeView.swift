import DesignSystem
import SwiftUI

public struct HomeView: View {
    @State private var viewModel = RoomViewModel()
    @State private var showJoinSheet = false

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
                Spacer()

                Text("マダミヌ")
                    .font(.mdLargeTitle)
                    .foregroundStyle(Color.mdPrimary)

                Text("AI Murder Mystery")
                    .font(.mdCallout)
                    .foregroundStyle(Color.mdTextSecondary)
                    .padding(.bottom, Spacing.xl)

                Spacer()

                VStack(spacing: Spacing.md) {
                    MDTextField(label: "あなたの名前", text: $viewModel.displayName, placeholder: "名前を入力")

                    if let error = viewModel.errorMessage {
                        Text(error)
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdError)
                    }

                    MDButton("ルームを作成", isLoading: viewModel.isLoading) {
                        Task { await viewModel.createRoom() }
                    }

                    MDButton("ルームに参加", style: .secondary) {
                        showJoinSheet = true
                    }
                }
                .padding(Spacing.lg)
                .padding(.bottom, Spacing.md)
            }
        }
        .onTapGesture {
            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
        }
        .sheet(isPresented: $showJoinSheet) {
            JoinRoomSheet(viewModel: viewModel, isPresented: $showJoinSheet)
        }
    }
}
