import SwiftUI

public struct MDTextField: View {
    let label: String
    @Binding var text: String
    var placeholder: String = ""

    public init(label: String, text: Binding<String>, placeholder: String = "") {
        self.label = label
        self._text = text
        self.placeholder = placeholder
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            Text(label)
                .font(.mdCaption)
                .foregroundStyle(Color.mdTextSecondary)

            TextField(placeholder, text: $text)
                .font(.mdBody)
                .padding(Spacing.sm)
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
