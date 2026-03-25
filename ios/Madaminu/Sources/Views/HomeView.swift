import DesignSystem
import SwiftUI

struct HomeView: View {
    @State private var viewModel = RoomViewModel()
    @State private var showJoinSheet = false

    var body: some View {
        if viewModel.isInRoom {
            RoomLobbyView(viewModel: viewModel)
        } else {
            homeContent
        }
    }

    private var homeContent: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.lg) {
                Spacer()

                Text("マダミヌ")
                    .font(.mdLargeTitle)
                    .foregroundStyle(Color.mdPrimary)

                Text("AI Murder Mystery")
                    .font(.mdCallout)
                    .foregroundStyle(Color.mdTextSecondary)

                Spacer()

                MDTextField(label: "あなたの名前", text: $viewModel.displayName, placeholder: "名前を入力")

                MDButton("ルームを作成", isLoading: viewModel.isLoading) {
                    Task { await viewModel.createRoom() }
                }

                MDButton("ルームに参加", style: .secondary) {
                    showJoinSheet = true
                }

                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdError)
                }

                Spacer().frame(height: Spacing.md)
            }
            .padding(Spacing.lg)
        }
        .sheet(isPresented: $showJoinSheet) {
            JoinRoomSheet(viewModel: viewModel, isPresented: $showJoinSheet)
        }
    }
}
