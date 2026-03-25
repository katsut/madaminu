import SwiftUI

public struct MDTextEditor: View {
    let label: String
    @Binding var text: String
    var minHeight: CGFloat = 100

    public init(label: String, text: Binding<String>, minHeight: CGFloat = 100) {
        self.label = label
        self._text = text
        self.minHeight = minHeight
    }

    public var body: some View {
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
