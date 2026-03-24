import SwiftUI

struct MDLoadingView: View {
    var message: String = ""

    var body: some View {
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
