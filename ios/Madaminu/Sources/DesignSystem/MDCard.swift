import SwiftUI

struct MDCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(Spacing.md)
            .background(Color.mdSurface)
            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))
    }
}
