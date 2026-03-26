import DesignSystem
import SwiftUI

struct TranscriptEditView: View {
    @ObservedObject var store: AppStore
    @State private var editedTranscript = ""
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.lg) {
                HStack {
                    Text("発言内容の確認・修正")
                        .font(.mdTitle2)
                        .foregroundStyle(Color.mdPrimary)
                    Spacer()
                }

                MDTextEditor(label: "文字起こし結果", text: $editedTranscript, minHeight: 150)

                Spacer()

                HStack(spacing: Spacing.md) {
                    MDButton("キャンセル", style: .secondary) {
                        dismiss()
                    }

                    MDButton("確定して送信") {
                        store.game.currentTranscript = editedTranscript
                        store.dispatch(.releaseSpeech)
                        dismiss()
                    }
                }
            }
            .padding(Spacing.lg)
        }
        .onAppear {
            editedTranscript = store.game.currentTranscript
        }
    }
}
