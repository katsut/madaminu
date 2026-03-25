import DesignSystem
import SwiftUI

struct RoomLobbyView: View {
    @Bindable var viewModel: RoomViewModel

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.md) {
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
        .sheet(isPresented: $viewModel.showCharacterCreation) {
            CharacterCreationView(viewModel: viewModel)
        }
    }

    private var header: some View {
        VStack(spacing: Spacing.xs) {
            Text("ルーム")
                .font(.mdCallout)
                .foregroundStyle(Color.mdTextSecondary)

            Text(viewModel.roomCode)
                .font(.mdLargeTitle)
                .foregroundStyle(Color.mdPrimary)
                .tracking(8)

            Text("\(viewModel.players.count)人が参加中")
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextMuted)
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
            if !viewModel.hasCreatedCharacter {
                MDButton("キャラクターを作成") {
                    viewModel.showCharacterCreation = true
                }
            } else if viewModel.canStartGame {
                MDButton("ゲーム開始", isLoading: viewModel.isLoading) {
                    // TODO: start game
                }
                .disabled(!viewModel.allPlayersReady)

                if !viewModel.allPlayersReady {
                    Text("全員のキャラクター作成を待っています...")
                        .font(.mdCaption)
                        .foregroundStyle(Color.mdTextMuted)
                }
            } else if viewModel.isHost {
                Text("4人以上でゲームを開始できます")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)
            } else {
                Text("ホストがゲームを開始するのを待っています...")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)
            }
        }
    }
}
