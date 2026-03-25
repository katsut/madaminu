import DesignSystem
import SwiftUI

struct JoinRoomSheet: View {
    @Bindable var viewModel: RoomViewModel
    @Binding var isPresented: Bool

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.lg) {
                HStack {
                    Text("ルームに参加")
                        .font(.mdTitle)
                        .foregroundStyle(Color.mdTextPrimary)
                    Spacer()
                    Button(action: { isPresented = false }) {
                        Image(systemName: "xmark")
                            .foregroundStyle(Color.mdTextSecondary)
                    }
                }

                MDTextField(label: "あなたの名前", text: $viewModel.displayName, placeholder: "名前を入力")

                MDTextField(label: "参加コード", text: $viewModel.joinCode, placeholder: "6文字のコード")

                MDButton("参加する", isLoading: viewModel.isLoading) {
                    Task {
                        await viewModel.joinRoom()
                        if viewModel.isInRoom {
                            isPresented = false
                        }
                    }
                }

                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdError)
                }

                Spacer()
            }
            .padding(Spacing.lg)
        }
    }
}
