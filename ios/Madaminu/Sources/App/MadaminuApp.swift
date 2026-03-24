import SwiftUI

@main
struct MadaminuApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .preferredColorScheme(.dark)
        }
    }
}

struct ContentView: View {
    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            VStack(spacing: Spacing.lg) {
                Text("マダミヌ")
                    .font(.mdLargeTitle)
                    .foregroundStyle(Color.mdPrimary)

                Text("AI Murder Mystery")
                    .font(.mdCallout)
                    .foregroundStyle(Color.mdTextSecondary)

                Spacer().frame(height: Spacing.xl)

                MDButton("ルームを作成") {}
                MDButton("ルームに参加", style: .secondary) {}
            }
            .padding(Spacing.lg)
        }
    }
}
