import SwiftUI

public struct MDLoadingView: View {
    var message: String = ""

    public init(message: String = "") {
        self.message = message
    }

    public var body: some View {
        VStack(spacing: Spacing.md) {
            ProgressView()
                .controlSize(.large)
                .tint(Color.mdPrimary)

            if !message.isEmpty {
                Text(message)
                    .font(.mdCallout)
                    .foregroundStyle(Color.mdTextSecondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.mdBackground)
    }
}
