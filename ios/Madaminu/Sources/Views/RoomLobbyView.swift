import DesignSystem
import SwiftUI

struct RoomLobbyView: View {
    @ObservedObject var store: AppStore
    @State private var copied = false

    var body: some View {
        ZStack {
            Color.mdBackground.ignoresSafeArea()

            VStack(spacing: Spacing.md) {
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

                VStack(spacing: Spacing.xs) {
                    Text("ルーム").font(.mdCallout).foregroundStyle(Color.mdTextSecondary)

                    Button {
                        UIPasteboard.general.string = store.room.roomCode
                        copied = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { copied = false }
                    } label: {
                        HStack(spacing: Spacing.xs) {
                            Text(store.room.roomCode).font(.mdLargeTitle).foregroundStyle(Color.mdPrimary).tracking(8)
                            Image(systemName: copied ? "checkmark" : "doc.on.doc")
                                .font(.mdCaption).foregroundStyle(copied ? Color.mdSuccess : Color.mdTextMuted)
                        }
                    }

                    Text(copied ? "コピーしました" : "\(store.room.players.count)人が参加中")
                        .font(.mdCaption).foregroundStyle(copied ? Color.mdSuccess : Color.mdTextMuted)
                }

                VStack(spacing: Spacing.xs) {
                    ForEach(store.room.players) { player in
                        MDCard {
                            HStack {
                                VStack(alignment: .leading, spacing: Spacing.xxs) {
                                    Text(player.displayName).font(.mdHeadline).foregroundStyle(Color.mdTextPrimary)
                                    if let cn = player.characterName {
                                        Text(cn).font(.mdCaption).foregroundStyle(Color.mdTextSecondary)
                                    }
                                }
                                Spacer()
                                if player.isHost {
                                    Text("ホスト").font(.mdCaption2).foregroundStyle(Color.mdPrimary)
                                        .padding(.horizontal, Spacing.xs).padding(.vertical, Spacing.xxs)
                                        .background(Color.mdPrimary.opacity(0.15))
                                        .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                                }
                                Image(systemName: player.characterName != nil ? "checkmark.circle.fill" : "circle.dashed")
                                    .foregroundStyle(player.characterName != nil ? Color.mdSuccess : Color.mdTextMuted)
                            }
                        }
                    }
                }

                Spacer()

                if !store.room.hasCreatedCharacter {
                    MDButton("キャラクターを作成") { store.dispatch(.showCharacterCreation) }
                } else if store.room.isHost {
                    MDButton("ゲーム開始", isLoading: store.isLoading) {
                        store.dispatch(.startGame)
                    }
                    let need = max(0, 4 - store.room.players.filter { $0.characterName != nil }.count)
                    if need > 0 {
                        Text("AIプレイヤーが\(need)人補充されます").font(.mdCaption).foregroundStyle(Color.mdPrimary)
                    }
                } else {
                    Text("ホストがゲームを開始するのを待っています...").font(.mdCaption).foregroundStyle(Color.mdTextMuted)
                }

                if let error = store.errorMessage {
                    Text(error).font(.mdCaption).foregroundStyle(Color.mdError)
                }
            }
            .padding(Spacing.lg)
        }
        .task {
            while store.screen == .lobby {
                store.dispatch(.refreshRoom)
                try? await Task.sleep(for: .seconds(3))
            }
        }
    }
}
