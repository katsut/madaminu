import SwiftUI

struct MDTextEditor: View {
    let label: String
    @Binding var text: String
    var minHeight: CGFloat = 100

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            Text(label)
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextSecondary)

            TextEditor(text: $text)
                .font(.mdBody)
                .frame(minHeight: minHeight)
                .padding(Spacing.xs)
                .scrollContentBackground(.hidden)
                .background(Color.mdBackgroundSecondary)
                .foregroundStyle(Color.mdTextPrimary)
                .clipShape(RoundedRectangle(cornerRadius: CornerRadius.sm))
                .overlay(
                    RoundedRectangle(cornerRadius: CornerRadius.sm)
                        .stroke(Color.mdSurfaceLight, lineWidth: 1)
                )
        }
    }
}
