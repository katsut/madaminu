import SwiftUI

struct MDModal<Content: View>: View {
    let title: String
    let content: Content
    let onDismiss: () -> Void

    init(title: String, onDismiss: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.title = title
        self.onDismiss = onDismiss
        self.content = content()
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text(title)
                    .font(.mdTitle2)
                    .foregroundStyle(Color.mdTextPrimary)
                Spacer()
                Button(action: onDismiss) {
                    Image(systemName: "xmark")
                        .foregroundStyle(Color.mdTextSecondary)
                }
            }
            .padding(Spacing.md)

            Divider()
                .background(Color.mdSurfaceLight)

            content
                .padding(Spacing.md)
        }
        .background(Color.mdSurface)
        .clipShape(RoundedRectangle(cornerRadius: CornerRadius.lg))
        .padding(Spacing.lg)
    }
}
