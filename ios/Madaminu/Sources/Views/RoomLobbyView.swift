import DesignSystem
import SwiftUI

struct RoomLobbyView: View {
    @ObservedObject var viewModel: RoomViewModel

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.md) {
                HStack {
                    Button {
                        viewModel.leaveRoom()
                    } label: {
                        HStack(spacing: Spacing.xxs) {
                            Image(systemName: "chevron.left")
                            Text("退出")
                        }
                        .font(.mdCallout)
                        .foregroundStyle(Color.mdTextSecondary)
                    }
                    Spacer()
                }

                header
                playerList
                Spacer()
                bottomActions
            }
            .padding(Spacing.lg)
        }
        .task {
            while viewModel.isInRoom {
                await viewModel.refreshRoom()
                try? await Task.sleep(for: .seconds(3))
            }
        }
        .fullScreenCover(isPresented: $viewModel.showCharacterCreation) {
            CharacterCreationView(viewModel: viewModel)
        }
    }

    @State private var copied = false

    private var header: some View {
        VStack(spacing: Spacing.xs) {
            Text("ルーム")
                .font(.mdCallout)
                .foregroundStyle(Color.mdTextSecondary)

            Button {
                UIPasteboard.general.string = viewModel.roomCode
                copied = true
                Task { @MainActor in
                    try? await Task.sleep(for: .seconds(2))
                    copied = false
                }
            } label: {
                HStack(spacing: Spacing.xs) {
                    Text(viewModel.roomCode)
                        .font(.mdLargeTitle)
                        .foregroundStyle(Color.mdPrimary)
                        .tracking(8)

                    Image(systemName: copied ? "checkmark" : "doc.on.doc")
                        .font(.mdCaption)
                        .foregroundStyle(copied ? Color.mdSuccess : Color.mdTextMuted)
                }
            }

            Text(copied ? "コピーしました" : "\(viewModel.players.count)人が参加中")
                .font(.mdCaption)
                .foregroundStyle(copied ? Color.mdSuccess : Color.mdTextMuted)
        }
        .padding(.top, Spacing.md)
    }

    private var playerList: some View {
        VStack(spacing: Spacing.xs) {
            ForEach(viewModel.players) { player in
                MDCard {
                    HStack {
                        VStack(alignment: .leading, spacing: Spacing.xxs) {
                            Text(player.displayName)
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdTextPrimary)

                            if let charName = player.characterName {
                                Text(charName)
                                    .font(.mdCaption)
                                    .foregroundStyle(Color.mdTextSecondary)
                            }
                        }

                        Spacer()

                        if player.isHost {
                            Text("ホスト")
                                .font(.mdCaption2)
                                .foregroundStyle(Color.mdPrimary)
                                .padding(.horizontal, Spacing.xs)
                                .padding(.vertical, Spacing.xxs)
                                .background(Color.mdPrimary.opacity(0.15))
                                .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                        }

                        if player.characterName != nil {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(Color.mdSuccess)
                        } else {
                            Image(systemName: "circle.dashed")
                                .foregroundStyle(Color.mdTextMuted)
                        }
                    }
                }
            }
        }
    }

    private var bottomActions: some View {
        VStack(spacing: Spacing.sm) {
            if let progress = viewModel.progressMessage {
                VStack(spacing: Spacing.sm) {
                    ProgressView()
                        .tint(Color.mdPrimary)
                    Text(progress)
                        .font(.mdCallout)
                        .foregroundStyle(Color.mdPrimary)
                }
                .padding(Spacing.md)
            } else if !viewModel.hasCreatedCharacter {
                MDButton("キャラクターを作成") {
                    viewModel.showCharacterCreation = true
                }
            } else if viewModel.isHost {
                MDButton("ゲーム開始", isLoading: viewModel.isLoading) {
                    Task { @MainActor in await viewModel.startGame() }
                }

                let humanReady = viewModel.players.filter { $0.characterName != nil }.count
                let aiNeeded = max(0, 4 - humanReady)

                if aiNeeded > 0 {
                    Text("AIプレイヤーが\(aiNeeded)人補充されます")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdPrimary)
                } else if !viewModel.allPlayersReady {
                    Text("全員のキャラクター作成を待っています...")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextMuted)
                }
            } else {
                Text("ホストがゲームを開始するのを待っています...")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)
            }

            if let error = viewModel.errorMessage {
                Text(error)
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdError)
                    .multilineTextAlignment(.center)
            }
        }
    }
}
