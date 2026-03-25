import SwiftUI

public struct MDCard<Content: View>: View {
    let content: Content

    public init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    public var body: some View {
        content
            .padding(Spacing.md)
            .background(Color.mdSurface)
            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))
    }
}
