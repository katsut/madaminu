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
                .onTapGesture {
                    dismissKeyboard()
                }

            ScrollViewReader { proxy in
                ScrollView {
                    VStack(spacing: Spacing.lg) {
                        Spacer().frame(height: Spacing.xxl)

                        Text("マダミヌ")
                            .font(.mdLargeTitle)
                            .foregroundStyle(Color.mdPrimary)

                        Text("AI Murder Mystery")
                            .font(.mdCallout)
                            .foregroundStyle(Color.mdTextSecondary)

                        Spacer().frame(height: Spacing.xl)

                        MDTextField(label: "あなたの名前", text: $viewModel.displayName, placeholder: "名前を入力")
                            .onTapGesture {
                                withAnimation {
                                    proxy.scrollTo("buttons", anchor: .bottom)
                                }
                            }

                        MDButton("ルームを作成", isLoading: viewModel.isLoading) {
                            dismissKeyboard()
                            Task { await viewModel.createRoom() }
                        }

                        MDButton("ルームに参加", style: .secondary) {
                            dismissKeyboard()
                            showJoinSheet = true
                        }
                        .id("buttons")

                        if let error = viewModel.errorMessage {
                            Text(error)
                                .font(.mdCaption)
                                .foregroundStyle(Color.mdError)
                        }

                        Spacer().frame(height: Spacing.xxl)
                    }
                    .padding(Spacing.lg)
                }
                .scrollDismissesKeyboard(.interactively)
            }
        }
        .sheet(isPresented: $showJoinSheet) {
            JoinRoomSheet(viewModel: viewModel, isPresented: $showJoinSheet)
        }
    }

    private func dismissKeyboard() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
}
